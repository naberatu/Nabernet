"""
AUTHOR:             Nader K. Atout
FACULTY ADVISOR:    Dr. Nader Bagherzadeh
GRADUATE MENTOR:    Mohammed Alnemari
PURPOSE:            UCI CHC Undergaduate Research Thesis (2020-2021)
TOPIC:              Using a Multiclass Segmentation model (U-Net) to determine the presence & severity of COVID-19
                        in human lungs, and compressing the model for low-resource devices.
REFERENCES:
    Medical Segmentation        (For provided Dataset ~ https://medicalsegmentation.com/covid19/)
    Rudolph Peinaar             (For Med2Image ~ Converting .NII files into .JPG)
    GitHub user Milesial        (Training, Testing, and logging routine templates ~ https://github.com/milesial)
    @PtrBlk & Pytorch forums    (For help with color-maps, & dataset setup/processing)
    Dr. Sreenivas Bhattiprolu   (YouTube: 208 Multiclass semantic segmentation with U-Net)
"""

# ===================================================
# NOTE: Imports
# ===================================================
# OS & Environment setup
import math
import os
import logging
import tifffile
import random
import warnings
import tempfile
import sys

# random.seed(12)
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
logging.getLogger('tensorflow').setLevel(logging.FATAL)

# General imports
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow import lite
import tensorflow_model_optimization as tfmot
import tensorflow.compat.v1 as tf_v1
from un_multi_model import multi_unet_model
import numpy as np
from un_eval import eval

# Keras and LabelEncoder
from tensorflow.python.keras import backend as K
from keras.utils import normalize
from keras.utils import to_categorical
import keras.metrics
from keras.metrics import MeanIoU
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.utils import class_weight

# ===================================================
# NOTE: Globals
# ===================================================
# Directories
dir_medseg = './data/MedSeg/'
dir_sandstone = 'C:/Users/elite/Desktop/sandstone_data_for_ML/full_labels_for_deep_learning/128_patches/'

# Other global variables
DEVICE = '/physical_device:GPU:0'
config = tf_v1.ConfigProto(device_count={'GPU': 1, 'CPU': 8})
K.set_session(tf_v1.Session(config=config))

# =============================================================
# NOTE: Model Parameters
# =============================================================

TRAIN_IMAGS = []
TRAIN_MASKS = []

# dir_ims = "images/"
# dir_masks = "masks/"
dir_ims = "images1/"
dir_masks = "masks1/"

# Read from TIFF images (MedSeg).
DATASET = "MedSeg"
for tif in os.listdir(dir_medseg + dir_ims):
    ims = np.array(tifffile.imread(dir_medseg + dir_ims + tif))
    for img in ims:
        TRAIN_IMAGS.append(img)
for tif in os.listdir(dir_medseg + dir_masks):
    masks = np.array(tifffile.imread(dir_medseg + dir_masks + tif)).astype(np.int8)
    for img in masks:
        TRAIN_MASKS.append(img)
TRAIN_IMAGS = np.asarray(TRAIN_IMAGS)
TRAIN_MASKS = np.asarray(TRAIN_MASKS).astype(np.int8)
IM_SIZE = 512
CLASSES = ["Backgnd/Misc", 'Ground Glass', 'Consolidation', 'Pleural Eff.']

# Read from TIFF images (Sandstone).
# DATASET = "Sandstone"
# TRAIN_IMAGS = np.array(tifffile.imread(dir_sandstone + "images.tiff"))
# TRAIN_MASKS = np.array(tifffile.imread(dir_sandstone + "masks.tiff")).astype(np.int8)
# IM_SIZE = 128       # Due to 128 x 128 patch images.
# CLASSES = ["Backgd", 'Clay', 'Quartz', 'Pyrite']

N_CLASSES = len(CLASSES)
EPOCHS = 100
BATCH_SIZE = 4      # Selected for RTX 2060
# VERBOSITY = 1       # Progress Bar
VERBOSITY = 2       # One Line/Epoch
# SHUFFLE = True
SHUFFLE = False
OPTIMIZER = tf.keras.optimizers.Adam(lr=0.0005)
# OPTIMIZER = "adam"

# =============================================================
# NOTE: Encoding & Pre-processing.
# =============================================================
# plt.imshow(TRAIN_IMAGS[24], cmap="gray")
# plt.show()
# plt.imshow(TRAIN_MASKS[24])
# plt.show()

# Assign labels & encode them.
labeler = LabelEncoder()
n, h, w = TRAIN_MASKS.shape
reshaped_masks = TRAIN_MASKS.reshape(-1, 1)
encoded_masks = labeler.fit_transform(reshaped_masks)
updated_masks = encoded_masks.reshape(n, h, w)

# Prepare training datasets.
TRAIN_IMAGS = np.expand_dims(TRAIN_IMAGS, axis=3)
TRAIN_IMAGS = normalize(TRAIN_IMAGS, axis=1)            # NOTE: Normalization step
input_masks = np.expand_dims(updated_masks, axis=3)

# Create training & testing datasets.
N_TEST = 0.1
x_train, x_test, y_train, y_test = train_test_split(TRAIN_IMAGS, input_masks, test_size=N_TEST, random_state=0)

# Sanity check
# print("Class values in the dataset are ... ", np.unique(y_train))

# Categorize by one-hot encoding.
masks_cat_train = to_categorical(y_train, num_classes=N_CLASSES)
y_train_cat = masks_cat_train.reshape((y_train.shape[0], y_train.shape[1], y_train.shape[2], N_CLASSES))
masks_cat_test = to_categorical(y_test, num_classes=N_CLASSES)
y_test_cat = masks_cat_test.reshape((y_test.shape[0], y_test.shape[1], y_test.shape[2], N_CLASSES))

# Calculate class weights.
# weights = class_weight.compute_class_weight('balanced', np.unique(encoded_masks), encoded_masks)
# weights = [0.00000000001, 1, 15, 10000000000000000]
# weights = [0.00000001, 100, 1000, 10000]
# weights = [0.00000001, 1, 10, 1000000000]
# print("Class weights are...:", weights, "\n")

IM_HT = x_train.shape[1]
IM_WD = x_train.shape[2]
IM_CH = x_train.shape[3]


def get_model():
    return multi_unet_model(n_classes=N_CLASSES, IMG_HEIGHT=IM_HT, IMG_WIDTH=IM_WD, IMG_CHANNELS=IM_CH)


# # =============================================================
# # NOTE: Compile and Fit Model.
# # =============================================================
# model = get_model()
# model.compile(optimizer=OPTIMIZER, loss='categorical_crossentropy',
#               metrics=[keras.metrics.MeanIoU(num_classes=N_CLASSES)])
# history = model.fit(x_train, y_train_cat, batch_size=BATCH_SIZE, verbose=VERBOSITY, epochs=EPOCHS,
#                     validation_data=(x_test, y_test_cat), class_weight=weights, shuffle=SHUFFLE)
# model.save(DATASET + ".hdf5")
#
# # =============================================================
# # NOTE: Metrics & Evaluation.
# # =============================================================
# model.load_weights(DATASET + ".hdf5")
# eval(FNAME="un_metrics_temp", DATASET=DATASET, MODEL=model, BATCH=BATCH_SIZE, EPOCHS=EPOCHS, CLASSES=CLASSES,
#      NUM_IMS=len(TRAIN_IMAGS), IM_DIM=IM_SIZE, IM_CH=IM_CH, TEST_IMS=x_test, TEST_MASKS=y_test, PRINT=True)
#
# # =============================================================
# # NOTE: Display Prediction.
# # =============================================================
# model = get_model()
# model.load_weights(DATASET + ".hdf5")
#
# # Predict on a few images
# ans = 0
# while True:
#     message = "Image to Predict on (0-" + str(len(x_test)) + "): \t"
#     ans = input(message)
#     try:
#         ans = int(ans)
#         if ans > len(x_test) or ans < 0:
#             raise Exception
#             # test_img_number = random.randint(0, len(x_test) - 1)
#         test_img_number = ans
#         test_img = x_test[test_img_number]
#         ground_truth = y_test[test_img_number]
#         test_img_norm = test_img[:, :, 0][:, :, None]
#         test_img_input = np.expand_dims(test_img_norm, 0)
#         prediction = (model.predict(test_img_input))
#         predicted_img = np.argmax(prediction, axis=3)[0, :, :]
#
#         plt.figure(figsize=(12, 8))
#         plt.subplot(231)
#         plt.title('Testing Image ' + str(test_img_number))
#         plt.imshow(test_img[:, :, 0], cmap='gray')
#         plt.subplot(232)
#         plt.title('Testing Label')
#         plt.imshow(ground_truth[:, :, 0], cmap='jet')
#         plt.subplot(233)
#         plt.title('Prediction on test image')
#         plt.imshow(predicted_img, cmap='jet')
#         plt.show()
#
#     except:
#         print("Exiting...")
#         break

# =============================================================
# NOTE: BEGIN PRUNING
# =============================================================

model = get_model()
model.load_weights(DATASET + ".hdf5")
model.compile(optimizer='adam', loss='categorical_crossentropy',
              metrics=[keras.metrics.MeanIoU(num_classes=N_CLASSES)])

with open('un_origin_summary.txt', 'w') as f:
    model.summary(print_fn=lambda x: f.write(x + '\n'))
f.close()

prune_low_magnitude = tfmot.sparsity.keras.prune_low_magnitude

# Compute end step to finish pruning after 2 epochs.
prune_epochs = 2
validation_split = 0.1      # 10% of training set will be used for validation set.

num_images = TRAIN_IMAGS.shape[0] * (1 - validation_split)
end_step = np.ceil(num_images / BATCH_SIZE).astype(np.int32) * prune_epochs

# Define model for pruning.
pruning_params = {
      'pruning_schedule': tfmot.sparsity.keras.PolynomialDecay(initial_sparsity=0.00,
                                                               final_sparsity=0.50,
                                                               begin_step=0,
                                                               end_step=end_step)
}

model_for_pruning = prune_low_magnitude(model, **pruning_params)
model_for_pruning.compile(optimizer='adam',
                          loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                          metrics=[keras.metrics.MeanIoU(num_classes=N_CLASSES)])

# with open('un_pruned_summary.txt', 'w') as f:
#     model_for_pruning.summary(print_fn=lambda x: f.write(x + '\n'))
# f.close()

# =============================================================
# NOTE: EVALUATE PRUNED MODEL
# =============================================================
eval(FNAME="un_metrics_prune", DATASET=DATASET, MODEL=model_for_pruning, CLASSES=CLASSES,
     NUM_IMS=len(TRAIN_IMAGS), IM_DIM=IM_SIZE, IM_CH=IM_CH, TEST_IMS=x_test, TEST_MASKS=y_test)

# =============================================================
# NOTE: EXPORT & COMPRESS PRUNED MODEL
# =============================================================
model_for_export = tfmot.sparsity.keras.strip_pruning(model_for_pruning)
model_for_export.save(DATASET + "_pruned.hdf5")
pruned_model = tf.keras.models.load_model(DATASET + "_pruned.hdf5")

with open('un_pruned_summary.txt', 'w') as f:
    pruned_model.summary(print_fn=lambda x: f.write(x + '\n'))
f.close()

print('Saved pruned Keras model to: ', pruned_model)

# converter = lite.TFLiteConverter.from_keras_model(model_for_export)
# pruned_tflite_model = converter.convert()
#
# _, pruned_tflite_file = tempfile.mkstemp('.tflite')
#
# with open(pruned_tflite_file, 'wb') as f:
#   f.write(pruned_tflite_model)
#
# print('Saved pruned TFLite model to: ', pruned_tflite_file)

# Returns size of gzipped model, in bytes.
# def get_gzipped_model_size(file):
#   import os
#   import zipfile
#
#   _, zipped_file = tempfile.mkstemp('.zip')
#   with zipfile.ZipFile(zipped_file, 'w', compression=zipfile.ZIP_DEFLATED) as f:
#     f.write(file)
#
#   return os.path.getsize(zipped_file)

# with open('C:\\Users\\elite\\PycharmProjects\\Pytorch\\un_gzip_info.txt', 'w') as f:
#     f.writelines('\n'.join(text))
# f.close()


# =============================================================
# NOTE: CONFIRM MODEL COMPRESSION SUCCESSFUL
# =============================================================
eval(FNAME="un_metrics_confirm", DATASET=DATASET, MODEL=pruned_model, CLASSES=CLASSES,
     NUM_IMS=len(TRAIN_IMAGS), IM_DIM=IM_SIZE, IM_CH=IM_CH, TEST_IMS=x_test, TEST_MASKS=y_test)
