#Sequence levels prediction
import loader as load, enricher as er, anomaly_detection as ad


dataset = "hdfs_s_parq" #hdfs, pro, hadoop, tb, tb-small

df = None
df_seq = None
loader = None

if dataset=="hadoop":
       loader = load.HadoopLoader(filename="../../../Datasets/hadoop/",
                                                 filename_pattern  ="*.log",
                                                 labels_file_name="../../../Datasets/hadoop/abnormal_label_accurate.txt")
elif dataset=="hdfs":
       loader = load.HDFSLoader(filename="../../../Datasets/hdfs/HDFS.log", 
                                          labels_file_name="../../../Datasets/hdfs/anomaly_label.csv")
elif dataset=="pro":
       loader = load.ProLoader(filename="../../../Datasets/profilence/*.txt")
elif dataset=="tb":
       loader = load.ThunderbirdLoader(filename="../../../Datasets/thunderbird/Thunderbird.log") #Might take 2-3 minutes in HPC cloud. In desktop out of memory
elif dataset=="tb-small":
       loader = load.ThunderbirdLoader(filename="../../../Datasets/thunderbird/Thunderbird_2k.log") #Only 2k lines
elif dataset=="hdfs_s_parq":
       import polars as pl
       df = pl.read_parquet("hdfs_events_002.parquet")
       df_seq = pl.read_parquet("hdfs_seqs_002.parquet")

if loader != None:
       df = loader.execute()
       if (dataset != "hadoop"):
              df = loader.reduce_dataframes(frac=0.02)
       df_seq = loader.df_sequences       
       if (dataset == "hdfs"):
              df.write_parquet("hdfs_events_002.parquet")
              df_seq.write_parquet("hdfs_seqs_002.parquet")
              

#df = loader.execute()
#if dataset!="hadoop":
#    df = loader.reduce_dataframes(frac=0.02)
#df_seq = loader.df_sequences

  
#-Event enrichment----------------------------------------------
#Parsing in event level
enricher = er.EventLogEnricher(df)
df = enricher.length()
df = enricher.parse_drain()
df = enricher.words()
df = enricher.alphanumerics()

#Collect events to sequence level as list[str]
seq_enricher = er.SequenceEnricher(df = df, df_sequences = df_seq)
seq_enricher.events()
seq_enricher.eve_len()
seq_enricher.start_time()
seq_enricher.end_time()
seq_enricher.seq_len()
seq_enricher.duration()
seq_enricher.tokens()


#Split
df_seq_train, df_seq_test = ad.test_train_split(seq_enricher.df_sequences, test_frac=0.95)

#Anomaly detection with Logstic Regression and DT----------------------------------------------

#Using tokens(words) from each sequence 
sad = ad.SupervisedAnomalyDetection(item_list_col="e_words")
sad.train_LR(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_DT(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_SVM(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_IsolationForest(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_RF(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_XGB(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)


# AD using only numeric columns:
#Defining numeric columns to be inclded
numeric_cols = ["seq_len", "eve_len_max", "duration_sec", "eve_len_over1"]
sad = ad.SupervisedAnomalyDetection(numeric_cols=numeric_cols)
sad.train_LR(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_DT(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_SVM(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_IsolationForest(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_RF(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_XGB(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)


# AD using only event column:
sad =  ad.SupervisedAnomalyDetection(item_list_col="events")
sad.train_LR(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_DT(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_SVM(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_IsolationForest(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_RF(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_XGB(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)


# AD using both
sad =  ad.SupervisedAnomalyDetection(item_list_col="events", numeric_cols=numeric_cols)
sad.train_LR(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_DT(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_SVM(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_IsolationForest(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_RF(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
sad.train_XGB(df_seq_train)
df_seq_test = sad.predict(df_seq_test, print_scores = True)
