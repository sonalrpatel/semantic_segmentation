import random
import glob
from pathlib import Path
from keras.models import load_model

from dataloader.dataloader import *
from utils.helpers import *
from utils.utils_metric import MeanIoU
from configs import *
from model.unet import *

import numpy as np
from matplotlib import pyplot as plt


def printinfo(
        checkpoint_path,
        test_generator
):
    """
    Print information about model testing
    """
    image_batch, label_batch = test_generator[0]
    num_classes = label_batch[0].shape[-1]
    print("\n")
    print("--> Model under trail: {}".format(checkpoint_path.split('/')[-2]))
    print("--> Testing batches: {}".format(len(test_generator)))
    print("--> Image size: {}".format(image_batch.shape))
    print("--> Label size: {}".format(label_batch.shape))
    print("--> No. of classes: {}".format(num_classes))
    print("\n")


# =======================================================
# Test the model
# =======================================================
def _main():
    image_size = IMAGE_SIZE
    classes_path = PATH_CLASSES
    num_classes, class_names, class_labels = get_class_info(classes_path)

    checkpoint_path = 'model_data/'
    test_mode = 'predict'
    model_name = MODEL_NAME
    encoder = MODEL_ENCODER
    encoder_weights = MODEL_ENCODER_WEIGHTS
    optimizer = MODEL_OPTIMIZER
    loss_type = MODEL_LOSS

    # Initialize miou metric with mean_per_class
    mean_per_class = (test_mode == "meaniou")
    conf_matrix = (test_mode == "confmat")
    calc_method = (conf_matrix is True)
    miou_metric = MeanIoU(num_classes, mean_per_class=mean_per_class,
                          conf_matrix=conf_matrix, calc_method=calc_method)

    # Find latest model checkpoint from the checkpoint_path
    latest_checkpoint = sorted(glob.glob(checkpoint_path + "*.h5"))[-1]
    print("--> Loading model from {}".format(latest_checkpoint))

    model_cfg = (num_classes, image_size, encoder, encoder_weights, model_name)
    model = unet(model_cfg)
    model.load_weights(latest_checkpoint)

    # Load model from checkpoint_path
    # model = load_model(latest_checkpoint,
    #                    custom_objects={
    #                        'mean_iou': miou_metric.mean_iou
    #                    }
    #                    )

    # Test pairs
    # =======================================================
    #   Validation settings
    # =======================================================
    val_images_path = DIR_VAL_IMG
    val_segs_path = DIR_VAL_SEG
    val_batch_size = VAL_BATCH_SIZE
    val_using = VAL_VALIDATION_USING
    val_split = VAL_VALIDATION_SPLIT
    test_pairs = get_pairs_from_paths(val_images_path, val_segs_path, '')

    # Create test generator
    test_generator = DataGenerator(test_pairs, class_labels, 8, dim=image_size)

    # Some information about the dataset
    printinfo(checkpoint_path, test_generator)

    if test_mode == "meaniou":
        # Find per class mean iou for whole test dataloader
        # shape of test_generator[b_no][0] is B*H*W*3
        # shape of test_generator[b_no][1] is B*H*W*N
        miou_per_class = []
        for b_no in tqdm(range(len(test_generator))):
            X_test, y_test = test_generator[b_no]
            y_pred = model.predict(X_test)

            miou_per_class_per_batch = miou_metric.mean_iou(y_test, y_pred)
            miou_per_class.append(np.array(miou_per_class_per_batch))

        # mean iou per class
        miou_per_class = np.mean(np.array(miou_per_class), axis=0).astype(float)

        # mean iou overall
        meaniou = np.mean(miou_per_class)
        print("--> Mean IoU for test dataset {}".format(meaniou))

        # # get per class pixel counts
        # df_class_count = count_pixels(test_segs_path, class_path)
        # df_class_count = df_class_count[pd.DataFrame(df_class_count.loc[0].sort_values(ascending=False)).T.columns]
        # columns = df_class_count.columns
        #
        # columns = ['road', 'unlabeled/static', 'sky', 'building', 'vegetation', 'car', 'sidewalk',
        #            'fence', 'pole/polegroup', 'terrain', 'truck', 'wall', 'bus', 'person', 'traffic sign',
        #            'traffic light', 'bicycle', 'rider', 'motorcycle', 'train']
        #
        # # prepare dataframe for per class mean iou
        # class_names, _ = get_class_info(class_path)
        # df_class_miou = pd.DataFrame(miou_per_class).T
        # df_class_miou.columns = class_names
        # df_class_miou = df_class_miou[columns]
        #
        # # plot
        # df_class_miou.loc[0].plot.bar()
        # plt.yscale("log")
        #
        # df_class_count.loc[0].plot.bar()

        return meaniou, miou_per_class

    if test_mode == "predict":
        # Display result for a random image
        randbatch = random.randint(0, len(test_generator) - 1)
        randimage = random.randint(0, test_generator.batch_size - 1)

        X_img = test_generator[randbatch][0][randimage]  # dim = H*W*3
        y_pred_label = make_prediction(model, img=X_img)  # dim = H*W

        y_true_label = test_generator[randbatch][1][randimage]  # dim = H*W*N
        y_true_label = np.argmax(y_true_label, axis=2)  # dim = H*W

        mapping = np.array(test_generator.class_labels)
        y_true_mask = form_color_mask(y_true_label, mapping)  # dim = H*W*3
        y_pred_mask = form_color_mask(y_pred_label, mapping)  # dim = H*W*3

        plt.imshow(y_true_mask)

        cv2.imshow('X_img', X_img)
        cv2.imshow('y_true_mask', y_true_mask)
        cv2.imshow('y_pred_mask', y_pred_mask)


if __name__ == '__main__':
    _main()
