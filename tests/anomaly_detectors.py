import sys
import glob
import os
import yaml
import polars as pl
import argparse
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
LOGLEAD_PATH = os.environ.get("LOGLEAD_PATH")
sys.path.append(os.environ.get("LOGLEAD_PATH"))
from loglead import AnomalyDetector

# Set up argument parser
parser = argparse.ArgumentParser(description='Dataset Loader Configuration')
parser.add_argument('--config', type=str, default='datasets.yml', help='Path to the YAML file containing dataset information. Default is datasets.yml.')
args = parser.parse_args()

# Read the configuration file
config_file = args.config
with open(config_file, 'r') as file:
    config = yaml.safe_load(file)

test_data_path = os.path.expanduser(config['root_folder'])
test_data_path = os.path.join(test_data_path, "test_data") 
 
# Get all .parquet files in the directory
all_files = glob.glob(os.path.join(test_data_path, "*.parquet"))

print("Anomaly detectors test starting.")
print(f"Found files {all_files}")
# Extract unique dataset names with '_eh_' , excluding '_seq' files
datasets = set()
for f in all_files:
    basename = os.path.basename(f)
    if "_lo" in basename and "_eh" in basename and "_seq" not in basename:
        dataset_name = basename.replace(".parquet", "")
        datasets.add(dataset_name)

cols_event = ["m_message", "e_words", "e_event_drain_id", "e_trigrams", "e_event_tip_id", "e_event_lenma_id", "e_bert_emb"] 
numeric_cols = ["seq_len", "eve_len_max", "duration_sec", "eve_len_over1", "nep_prob_nmax_avg", "nep_prob_nmax_min"]
for dataset in datasets:
    # Load the event level data
    primary_file = os.path.join(test_data_path, f"{dataset}.parquet")
    print(f"\nLoading {primary_file}")
    df = pl.read_parquet(primary_file)

    for col in cols_event:
        disabled_methods = set()
        disabled_methods.add("train_LOF") #Too slow. Disabled to make tests run faster
        disabled_methods.add("train_OneClassSVM") #Too slow. Disabled to make tests run faster
        if col == "m_message":
            disabled_methods.add("train_OOVDetector")
          #Only run if the predictor column AND anomaly labels are present AND we have at least two classes in the data
        if ((col == "e_trigrams" or col == "m_message") and "nezha_tt" in dataset):
            disabled_methods.add("train_RF") #Disable this slow combo. 
        if (col in df.columns and "anomaly" in df.columns and 
        df["normal"].sum() > 10 and
        df["anomaly"].sum() > 10):
            print(f"Running event anomaly detectors with {col}")
            sad = AnomalyDetector(item_list_col=col, print_scores= False, store_scores=True)
            sad.test_train_split (df, test_frac=0.5) 
            sad.evaluate_all_ads(disabled_methods=disabled_methods)


    seq_file = primary_file.replace(f"{dataset}.parquet", f"{dataset}_seq.parquet")
    if os.path.exists(seq_file):
        df_seq = pl.read_parquet(seq_file)
        print(f"Running seqeuence anomaly detectors with {seq_file}")
        for col in cols_event:
            disabled_methods = set()
            disabled_methods.add("train_LOF") #Too slow. Disabled to make tests run faster
            disabled_methods.add("train_OneClassSVM") #Too slow. Disabled to make tests run faster
            if col == "m_message":
                disabled_methods.add("train_OOVDetector")
                #Only run if the predictor column AND anomaly labels are present AND we have at least two classes in the data
            if (col in df_seq.columns and "anomaly" in df_seq.columns and 
            df_seq["normal"].sum() > 9 and
            df_seq["anomaly"].sum() > 9):
                print(f"Running seqeuence anomaly detectors with {col}")
                sad =  AnomalyDetector(item_list_col=col, print_scores= False, store_scores=True)
                #High training fraction to ensure we always have suffiecient samples as these are reduced dataframes 
                sad.test_train_split (df_seq, test_frac=0.2) 
                sad.evaluate_all_ads(disabled_methods=disabled_methods)
            else: 
                print (f"Column {col} missing or too low number (<11) of normal sequences { df_seq["normal"].sum()} or anomaly sequences {df_seq["anomaly"].sum()}")    
        print(f"Running seqeuence anomaly detectors with numeric columns {numeric_cols}")
        if ("anomaly" in df_seq.columns and 
        df_seq["normal"].sum() > 9 and
        df_seq["anomaly"].sum() > 9):
            disabled_methods = set()
            disabled_methods.add("train_RarityModel")
            disabled_methods.add("train_OOVDetector")
            sad = AnomalyDetector(numeric_cols = numeric_cols, print_scores= False, store_scores=True)
            #High training fraction to ensure we always have suffiecient samples as these are reduced dataframes 
            sad.test_train_split (df_seq, test_frac=0.2) 
            sad.evaluate_all_ads(disabled_methods=disabled_methods)

print("Anomaly detectors test complete.")