#Sequence levels prediction
import loader as load, enricher as er, anomaly_detection as ad


#Which one to run. Only one true. 
b_hadoop = False
b_hdfs = True
b_profilence = False


# Loading HDFS Logs----------------------------------------------------------------
#hdfs_processor = load.HDFSLoader(filename="../../../Datasets/hdfs/HDFS.log", 
#                                     labels_file_name="../../../Datasets/hdfs/anomaly_label.csv")
#df = hdfs_processor.execute()
#smaller hdfs for faster running. Parsing of whole HDFS takes about 11min
#df = hdfs_processor.reduce_dataframes(frac=0.2)

df = None
df_seq = None
preprocessor = None

if (b_hadoop):
       preprocessor = load.HadoopLoader(filename="../../../Datasets/hadoop/",
                                                 filename_pattern  ="*.log",
                                                 labels_file_name="../../../Datasets/hadoop/abnormal_label_accurate.txt")

elif (b_hdfs):
       preprocessor = load.HDFSLoader(filename="../../../Datasets/hdfs/HDFS.log", 
                                          labels_file_name="../../../Datasets/hdfs/anomaly_label.csv")

elif (b_profilence):
       preprocessor = load.ProLoader(filename="../../../Datasets/profilence/*.txt")

df = preprocessor.execute()
if (not b_hadoop):
    df = preprocessor.reduce_dataframes(frac=0.02)
df_seq = preprocessor.df_sequences

  
#-Event enrichment----------------------------------------------
#Parsing in event level
enricher_hdfs = er.EventLogEnricher(df)
df = enricher_hdfs.length()
df = enricher_hdfs.parse_drain()
#Collect events to sequence level as list[str]
seq_enricher = er.SequenceEnricher(df = df, df_sequences = df_seq)
seq_enricher.enrich_sequence_events()
seq_enricher.enrich_event_length()
seq_enricher.enrich_start_time()
seq_enricher.enrich_end_time()
seq_enricher.enrich_sequence_length()
seq_enricher.enrich_sequence_duration()

#Split
df_seq_train, df_seq_test = ad.test_train_split(seq_enricher.df_sequences, test_frac=0.5)

#Anomaly detection with Logstic Regression----------------------------------------------

# Using only numeric columns:
numeric_cols = ["seq_len", "event_max_len", "seq_dur_sec", "events_over_1_line"]

ad_seq = ad.SeqAnomalyDetection(df_seq_train, numeric_cols=numeric_cols)
# Using only event column:
ad_seq =  ad.SeqAnomalyDetection(df_seq_train, event_col="event_list")
#using both
ad_seq =  ad.SeqAnomalyDetection(df_seq_train, event_col="event_list", numeric_cols=numeric_cols)
#------------------------
ad_seq.train_LR()
df_seq_test = ad_seq.predict_LR(df_seq_test, print_scores = True)
