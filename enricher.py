import polars as pl
from drain3 import TemplateMiner

class EventLogEnricher:
    def __init__(self, df):
        self.df = df

    # Helper function to check if all prerequisites exist
    def _prerequisites_exist(self, prerequisites):
        return all([col in self.df.columns for col in prerequisites])

    # Helper function to handle prerequisite check and raise exception if missing
    def _handle_prerequisites(self, prerequisites):
        if not self._prerequisites_exist(prerequisites):
            raise ValueError(f"Missing prerequisites for enrichment: {', '.join(prerequisites)}")

    # Function-based enricher to split messages into words
    def words(self):
        self._handle_prerequisites(["m_message"])
        if "e_words" not in self.df.columns:
            self.df = self.df.with_columns(pl.col("m_message").str.split(by=" ").alias("e_words"))
        return self.df

    # Function-based enricher to extract alphanumeric tokens from messages
    def alphanumerics(self):
        self._handle_prerequisites(["m_message"])
        if "e_alphanumerics" not in self.df.columns:
            self.df = self.df.with_columns(
                pl.col("m_message").str.extract_all(r"[a-zA-Z\d]+").alias("e_alphanumerics")
            )
        return self.df

    # Function-based enricher to create trigrams from messages
    #Trigrams enrichment is slow 1M lines in 40s.
    #Trigram flag to be removed after this is fixed. 
    #https://github.com/pola-rs/polars/issues/10833
    #https://github.com/pola-rs/polars/issues/10890   
    def trigrams(self):
        self._handle_prerequisites(["m_message"])
        if "e_cgrams" not in self.df.columns:
            self.df = self.df.with_columns(
                pl.col("m_message").map_elements(
                    lambda mes: self._create_cngram(message=mes, ngram=3)).alias("e_cgrams")
            )
        return self.df

    def _create_cngram(self, message, ngram=3):
        if ngram <= 0:
            return []
        return [message[i:i+ngram] for i in range(len(message) - ngram + 1)]
    
    #Enrich with drain parsing results
    def parse_drain(self):
        self._handle_prerequisites(["m_message"])
        if "e_event_id" not in self.df.columns:
            # Drain returns dict
            # {'change_type': 'none',
            # 'cluster_id': 1,
            # 'cluster_size': 2,
            # 'template_mined': 'session closed for user root',
            # 'cluster_count': 1}
            self.tm = TemplateMiner()#we store template for later use.
            
            # We might have multiline log message, i.e. log_message + stack trace. 
            #Use only first line of log message for parsing
            self.df = self.df.with_columns(
                message_trimmed = pl.col("m_message").str.split("\n").list.first()
            )
            self.df = self.df.with_columns(drain = pl.col("message_trimmed").map_elements(lambda x: self.tm.add_log_message(x)))
            #self.df = self.df.with_columns(drain = pl.col("m_message").map_elements(lambda x: self.tm.add_log_message(x)))
            #tm.drain.print_tree()
            self.df = self.df.with_columns(
                e_event_id=pl.lit("e") + pl.col("drain").struct.field("cluster_id").cast(pl.Utf8),#extra thing ensure we e1 e2 instead of 1 2
                e_template = pl.col("drain").struct.field("template_mined"))
            self.df = self.df.drop("drain")#Drop the dictionary produced by drain. Event_id and template are the most important. 
        return self.df

    def length(self):
        self._handle_prerequisites(["m_message"])
        if "e_message_len" not in self.df.columns:
            self.df = self.df.with_columns(
                e_message_len_char = pl.col("m_message").str.n_chars(),
                e_message_len_lines = pl.col("m_message").str.count_matches(r"(\n|\r|\r\n)")
            )
        return self.df

class SequenceEnricher:
    def __init__(self, df, df_sequences):
        self.df = df
        self.df_sequences = df_sequences

    def start_time(self):
        df_temp = self.df.group_by('seq_id').agg(pl.col('m_timestamp').min().alias('start_time'))
        self.df_sequences = self.df_sequences.join(df_temp, on='seq_id')
        return self.df_sequences

    def end_time(self):
        df_temp = self.df.group_by('seq_id').agg(pl.col('m_timestamp').max().alias('end_time'))
        self.df_sequences = self.df_sequences.join(df_temp, on='seq_id')
        return self.df_sequences

    def seq_len(self):
        # Count the number of rows for each seq_id
        df_temp = self.df.group_by('seq_id').agg(pl.count().alias('seq_len'))
        # Join this result with df_sequences on seq_id
        self.df_sequences = self.df_sequences.join(df_temp, on='seq_id')
        return self.df_sequences
    
    def events(self):
        # Aggregate event ids into a list for each seq_id
        df_temp = self.df.group_by('seq_id').agg(
                events = pl.col('e_event_id')
            )
        # Join this result with df_sequences on seq_id
        self.df_sequences = self.df_sequences.join(df_temp, on='seq_id')
        return self.df_sequences


    def duration(self):
        # Calculate the sequence duration for each seq_id as the difference between max and min timestamps
        df_temp = self.df.group_by('seq_id').agg(
            (pl.col('m_timestamp').max() - pl.col('m_timestamp').min()).alias('duration'),
            (pl.col('m_timestamp').max() - pl.col('m_timestamp').min()).dt.seconds().alias('duration_sec')
        )
        # Join this result with df_sequences on seq_id
        self.df_sequences = self.df_sequences.join(df_temp, on='seq_id')
        return self.df_sequences
        
    def eve_len(self):
        # Count the number of rows for each seq_id
        df_temp = self.df.group_by('seq_id').agg(
            eve_len_max = pl.col('e_message_len_char').max(),
            eve_len_min = pl.col('e_message_len_char').min(),
            eve_len_avg = pl.col('e_message_len_char').mean(),
            eve_len_med = pl.col('e_message_len_char').median(),
            eve_len_over1 = (pl.col('e_message_len_char') > 1).sum()
            )
        # Join this result with df_sequences on seq_id
        self.df_sequences = self.df_sequences.join(df_temp, on='seq_id')
        return self.df_sequences    
