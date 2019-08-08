import os
import time

import tensorflow.keras.backend as K
import numpy as np
from itertools import product
from tensorflow.keras.regularizers import l2
from sklearn.utils import shuffle
from lstm_model import build_lstm_model
import sys
sys.path.append("....")
from utils.load_data import load_data
from utils.utils import add_experiment, save_experiments, model_evaluation,\
                        experiment_results_summary, generate_prediction_plots, train_test_split,\
                        apply_generate_sequences, data_standardization, compute_class_weight

os.environ["CUDA_VISIBLE_DEVICES"] = "2"
np.random.seed(42)

""" Global parameters """
cross_val = True
saving = True
num = 1

""" Neural network hyperparameters """
epochs = [15]
batch_size = 64
depth_lstm = [1]
depth_dense = [2]
units_lstm = [256]
reg_n = ['5e-1']
activation = 'relu'
batch_norm = True
dropout = [0.4]

""" Sequences hyperparameters """
subsampling_factor = [2]
stride = [1, 5]
look_back = [100, 200, 500]
target_steps_ahead = [0]  # starting from the position len(sequence)
predicted_timestamps = 1

""" Set tunables """
tunables_sequences = [subsampling_factor, stride, look_back, target_steps_ahead]
tunables_network = [epochs, depth_lstm, depth_dense, units_lstm, reg_n, dropout]

# -----------------------------------------------------------------------------
# DATA PREPROCESSING
# -----------------------------------------------------------------------------
""" Import dataset """
X, y, dataset, seizure = load_data()

""" Select training set and test set """
X_train_fold, y_train_fold, X_test_fold, y_test_fold = train_test_split(X, y, cross_val=cross_val)
n_folds = len(X_train_fold)

""" Iterate through fold-sets """
for fold in range(n_folds):
    fold_set = fold if cross_val else '/'
    if cross_val: print(f"Fold set: {fold_set}")

    X_train = X_train_fold[fold]
    y_train = y_train_fold[fold]
    X_test = X_test_fold[fold]
    y_test = y_test_fold[fold]

    class_weight = compute_class_weight(y_train)

    """ Standardize data """
    X_train, X_test = data_standardization(X_train, X_test)

    original_X_train = X_train
    original_y_train = y_train
    original_X_test = X_test
    original_y_test = y_test

    """ Iterate through sequences parameters """
    for subsampling_factor, stride, look_back, target_steps_ahead in product(*tunables_sequences):

        """ Generate subsampled sequences """
        X_train, y_train, X_test, y_test = \
            apply_generate_sequences(original_X_train, original_y_train,
                                     original_X_test, original_y_test,
                                     look_back, target_steps_ahead,
                                     stride, subsampling_factor)

        """ Shuffle training data """
        X_train_shuffled, y_train_shuffled = shuffle(X_train, y_train)

        print(X_train.shape, y_train.shape)
        print(X_test.shape, y_test.shape)

        """ Iterate through network parameters """
        for epochs, depth_lstm, depth_dense, units_lstm, reg_n,\
            dropout in product(*tunables_network):
            # -----------------------------------------------------------------------------
            # MODEL BUILDING, TRAINING AND TESTING
            # -----------------------------------------------------------------------------
            exp = "exp" + str(num)
            file_name = exp + "_lstm_pred.txt"
            print(f"\n{exp}\n")

            reg = l2(float(reg_n))

            """ Build the model """
            # input_shape = (X_train.shape[-2], X_train.shape[-1])
            model = build_lstm_model(depth_lstm, depth_dense, units_lstm,
                                     reg, activation, batch_norm, dropout)
            model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

            model.fit(X_train_shuffled, y_train_shuffled,
                      batch_size=batch_size,
                      epochs=epochs,
                      class_weight=class_weight)

            if saving:
                """ Save and reload the model """
                MODEL_PATH = "models/models_detection_final/"
                model.save(f"{MODEL_PATH}lstm_det_model{num}.h5")
                # del model
                # model = load_model(f"{MODEL_PATH}lstm_det_model{num}.h5")

            # -----------------------------------------------------------------------------
            # RESULTS EVALUATION
            # -----------------------------------------------------------------------------
            """ Predictions on training data """
            print("Predicting values on training data...")
            predictions_train = model.predict(X_train, batch_size=batch_size).flatten()
            loss_train, accuracy_train, roc_auc_train, recall_train = model_evaluation(predictions=predictions_train,
                                                                                       y=y_train)
            print("Results on training data")
            print(f"\tLoss:    \t{loss_train:.4f}")
            print(f"\tAccuracy:\t{accuracy_train:.4f}")
            print(f"\tROC-AUC: \t{roc_auc_train:.4f}")
            print(f"\tRecall:  \t{recall_train:.4f}")

            """ Predictions on test data """
            print("Predicting values on test data...")
            predictions_test = model.predict(X_test, batch_size=batch_size).flatten()
            loss_test, accuracy_test, roc_auc_test, recall_test = model_evaluation(predictions=predictions_test,
                                                                                   y=y_test)
            print("Results on test data")
            print(f"\tLoss:    \t{loss_test:.4f}")
            print(f"\tAccuracy:\t{accuracy_test:.4f}")
            print(f"\tROC-AUC: \t{roc_auc_test:.4f}")
            print(f"\tRecall:  \t{recall_test:.4f}")

            # -----------------------------------------------------------------------------
            # EXPERIMENT RESULTS SUMMARY
            # -----------------------------------------------------------------------------
            if saving:
                RESULTS_PATH = f"results/results_detection_final/{file_name}"
                title = "LSTM NEURAL NETWORK"
                shapes = {
                    "X_train": X_train.shape,
                    "y_train": y_train.shape,
                    "X_test": X_test.shape,
                    "y_test": y_test.shape
                }
                parameters = {
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "depth_lstm": depth_lstm,
                    "depth_dense": depth_dense,
                    "units_lstm": units_lstm,
                    "reg_n": f"l2({reg_n})",
                    "activation": activation,
                    "batch_norm": str(batch_norm),
                    "dropout": dropout,
                    "class_weight": str(class_weight),
                    "look_back": look_back,
                    "stride": stride,
                    "predicted_timestamps": predicted_timestamps,
                    "target_steps_ahead": target_steps_ahead,
                    "subsampling_factor": subsampling_factor
                }
                results_train = {
                    "loss_train": loss_train,
                    "accuracy_train": accuracy_train,
                    "roc_auc_train": roc_auc_train,
                    "recall_train": recall_train
                }
                results_test = {
                    "loss_test": loss_test,
                    "accuracy_test": accuracy_test,
                    "roc_auc_test": roc_auc_test,
                    "recall_test": recall_test
                }
                string_list = []
                model.summary(print_fn=lambda x: string_list.append(x))
                summary = "\n".join(string_list)

                experiment_results_summary(RESULTS_PATH, num, title, summary, shapes, parameters, results_train, results_test)

                EXP_FILENAME = "experiments_lstm_det_final"
                hyperpar = ['', 'epochs', 'depth_lstm', 'depth_dense', 'units_lstm', 'activation',
                            'l2_reg', 'batch_norm', 'dropout', 'stride', 'subsampling_factor', 'look_back',
                            'target_steps_ahead', 'fold_set', 'loss', 'acc', 'roc-auc', 'recall']
                exp_hyperpar = [epochs, depth_lstm, depth_dense, units_lstm, activation,
                                reg_n, batch_norm, dropout, stride, subsampling_factor, look_back,
                                target_steps_ahead, fold_set,
                                f"{loss_test:.5f}", f"{accuracy_test:.5f}", f"{roc_auc_test:.5f}", f"{recall_test:.5f}"]
                df = add_experiment(EXP_FILENAME, num, hyperpar, exp_hyperpar)
                save_experiments(EXP_FILENAME, df)

                # -----------------------------------------------------------------------------
                # PLOTS
                # -----------------------------------------------------------------------------
                PLOTS_PATH = "./plots/plots_detection_final/"

                PLOTS_FILENAME = f"{PLOTS_PATH}{exp}_det-predictions_train.png"
                generate_prediction_plots(PLOTS_FILENAME, predictions=predictions_train, y=y_train, moving_a=100)

                PLOTS_FILENAME = f"{PLOTS_PATH}{exp}_det-predictions.png"
                generate_prediction_plots(PLOTS_FILENAME, predictions=predictions_test, y=y_test, moving_a=100)

            num += 1
            K.clear_session()