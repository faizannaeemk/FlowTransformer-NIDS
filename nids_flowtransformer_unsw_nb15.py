import tensorflow as tf
print(tf. __version__)

"""Create a directory to store our data"""

import os

demonstration_folder = "demonstration"

# if not os.path.exists(demonstration_folder):
#     os.mkdir(demonstration_folder)
#
# """Download data from
# https://staff.itee.uq.edu.au/marius/NIDS_datasets/#RA6.
#
# Here, we have loaded the data to our google drive and we mount that to get the data.
# """
#
# import shutil
#
# # copy the dataset from the drve to the demonstration folder
# shutil.copy("./fe6cb615d161452c_MOHANAD_A4706.zip",
#             os.path.join(demonstration_folder, "dataset.zip"))
#
# """Extract Data"""
#
# import zipfile
#
# zip_path = os.path.join(demonstration_folder, "dataset.zip")
csv_path = os.path.join(demonstration_folder, "dataset.csv")
#
# if not os.path.exists(csv_path):
#     with zipfile.ZipFile(zip_path, "r") as zip_ref:
#         zip_ref.extract("fe6cb615d161452c_MOHANAD_A4706/data/NF-UNSW-NB15-v2.csv", demonstration_folder)
#         inner_path = os.path.join(demonstration_folder, "fe6cb615d161452c_MOHANAD_A4706/data/NF-UNSW-NB15-v2.csv")
#         os.rename(inner_path, csv_path)
#
# print(f"Dataset is available at {csv_path}, size = {os.path.getsize(csv_path):,}")

"""Setup flow transformer model"""

from itertools import product
from framework.flow_transformer_parameters import FlowTransformerParameters
from framework.flow_transformer import FlowTransformer
from implementations.classification_heads import (LastTokenClassificationHead,
                                                  FlattenClassificationHead,
                                                  FeaturewiseEmbedding,
                                                  GlobalAveragePoolingClassificationHead,
                                                  CLSTokenClassificationHead)
from implementations.input_encodings import (RecordLevelEmbed,
                                             NoInputEncoder,
                                             CategoricalFeatureEmbed,
                                             EmbedLayerType)

from implementations.pre_processings import StandardPreProcessing
from implementations.transformers.basic_transformers import BasicTransformer

# Make a dictionary of six types of classification heads
classification_heads = {
    "Last token": LastTokenClassificationHead(), # Last token
    "Flatten": FlattenClassificationHead(),  # Flatten
    "Featurewise emb.": FeaturewiseEmbedding(project=False),  # Featurewise emb.
    "Featurewise projection": FeaturewiseEmbedding(project=True), # Featurewise projection
    "Global average pooling": GlobalAveragePoolingClassificationHead(), # Global average pooling
    "CLS token": CLSTokenClassificationHead()} # CLS token

# Make a dictionary of six types of encodings
encodings = {
    "Categorical emb. dense": CategoricalFeatureEmbed(EmbedLayerType.Dense, 16), # Categorical emb. dense
    "Categorical emb. lookup": CategoricalFeatureEmbed(EmbedLayerType.Lookup, 16), # Categorical emb. lookup
    "Categorical projection": CategoricalFeatureEmbed(EmbedLayerType.Projection, 16), # Categorical projection
    "Record emb. dense": RecordLevelEmbed(64), # Record emb. dense
    "Record projection": RecordLevelEmbed(64, project=True), # Record projection
    "No input encoding": NoInputEncoder()} # No input encoding

# Generate all combinations
combinations = list(product(classification_heads.keys(), encodings.keys()))
for i, combination in enumerate(combinations):
    print(f"Combination {i+1}: {combination}")

from framework.dataset_specification import NamedDatasetSpecifications
from framework.enumerations import EvaluationDatasetSampling
from IPython.display import display
import pandas as pd
import time

def evaluate_combination(classification_head, encoding):
  start_time = time.time()

  # We use several standard component to build our transformer
  pre_processing = StandardPreProcessing(n_categorical_levels=32)
  transformer = BasicTransformer(n_layers=2, internal_size=128, n_heads=2)

  # Define the transformer
  ft = FlowTransformer(pre_processing=pre_processing,
                      input_encoding=encoding,
                      sequential_model=transformer,
                      classification_head=classification_head,
                      params=FlowTransformerParameters(window_size=8, mlp_layer_sizes=[128], mlp_dropout=0.1))

  # Use the FlowTransformer instant to load and preprocess the dataset csv file
  dataset_name = "UNSW_NB15"
  dataset_path = csv_path
  dataset_specification = NamedDatasetSpecifications.unified_flow_format
  eval_percent = 0.025
  eval_method = EvaluationDatasetSampling.LastRows
  ft.load_dataset(dataset_name,
                  dataset_path,
                  dataset_specification,
                  evaluation_dataset_sampling=eval_method,
                  evaluation_percent=eval_percent,
                  cache_path=demonstration_folder)

  # Build and compile the transfomer model
  m = ft.build_model(cls_type='multiclass')
  parameters = m.count_params()

  # Compile the model
  # m.compile(optimizer="adam", loss='binary_crossentropy',
  #         metrics=['binary_accuracy'], jit_compile=True)

  m.compile(
      optimizer="adam",
      loss='sparse_categorical_crossentropy',  # Use 'categorical_crossentropy' if your labels are not one-hot encoded
      metrics=['accuracy'],
      jit_compile=True
  )

  # Get the evaluation results
  (train_results, eval_results, final_epoch) = ft.evaluate(m, batch_size=128, epochs=5, steps_per_epoch=64, early_stopping_patience=5)
  end_time = time.time()
  # Calculate the elapsed time
  elapsed_time = end_time - start_time

  return {'results': eval_results, 'time': elapsed_time, 'params': parameters}

"""Evaluate Model"""

# Evaluate all combinations
results = {}
for i, combination in enumerate(combinations):
    print(f"\n######################################################################")
    print(f"Evaluating combination {i+1}: {combination}\n")
    cls_head = classification_heads[combination[0]]
    enc = encodings[combination[1]]
    results[combination] = evaluate_combination(cls_head, enc)

# save results
import pickle
with open('/content/drive/MyDrive/results_nids.pickle', 'wb') as handle:
    pickle.dump(results, handle, protocol=pickle.HIGHEST_PROTOCOL)

# Reload the pickle file
with open('/content/drive/MyDrive/results_nids.pickle', 'rb') as handle:
    results = pickle.load(handle)

for i, combination in enumerate(combinations):
    print(f"\n######################################################################")
    print(f"Results combination {i+1}: {combination}\n")
    print(f"Results:\n {results[combination]['results']}")
    print(f"Time: {results[combination]['time']}")
    print(f"Parameters: {results[combination]['params']}")

"""False Alarm Rate (FAR) = FP+TN/FP

Detection Rate = TP/P

"""