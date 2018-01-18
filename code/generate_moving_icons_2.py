"""ICLRw experiments as of 12/21/17"""

import multiprocessing
import os

import numpy as np

from moving_icons import MovingIconEnvironment, AbstractMovingIconSubscriber

class MovingIconClassTrajectoryTracker(AbstractMovingIconSubscriber):
    """Object that gets the icon classes and trajectories of the generated video"""

    def __init__(self):
        self.icon_classes = {}
        self.trajectories = {}


    def process_message(self, message):
        """Store the message."""
        meta = message['meta']
        if message['type'] == 'icon_init':
            self.icon_classes[meta['icon_id']] = meta['label']
        elif message['type'] == 'icon_state':
            if meta['icon_id'] not in self.trajectories:
                self.trajectories[meta['icon_id']] = []
            self.trajectories[meta['icon_id']].append(meta['position'])

    def get_info(self):
        """Return the trajectories and icon classes

        :return: num_icons np.array, num_icons x T x 2 np.array
        """
        sorted_keys = sorted(self.icon_classes.keys())
        icon_classes_np = np.array([self.icon_classes[k] for k in sorted_keys])
        for k in sorted_keys:
            self.trajectories[k] = np.stack(self.trajectories[k], axis=0)
        trajectories_np = np.stack([self.trajectories[k] for k in sorted_keys], axis=0)
        return icon_classes_np, trajectories_np


def get_param_dicts():
    # Generalizing rate, slow -> fast
    mnist_training_slow_params = {
        'data_dir': '../data/mnist',
        'split': 'training',
        'color_output': False,
        'icon_labels': range(10),
        'position_speed_limits': (1, 5)
    }
    mnist_training_fast_params = {
        'data_dir': '../data/mnist',
        'split': 'training',
        'color_output': False,
        'icon_labels': range(10),
        'position_speed_limits': (1, 5)
    }
    mnist_testing_fast_params = {
        'data_dir': '../data/mnist',
        'split': 'testing',
        'color_output': False,
        'icon_labels': range(10),
        'position_speed_limits': (6, 9)
    }

    # Generalizing rate, slow & fast -> medium
    mnist_training_slow_fast_params = {
        'data_dir': '../data/mnist',
        'split': 'training',
        'color_output': False,
        'icon_labels': range(10),
        'position_speed_limits': [(1, 3), (7, 9)]
    }
    mnist_training_medium_params = {
        'data_dir': '../data/mnist',
        'split': 'training',
        'color_output': False,
        'icon_labels': range(10),
        'position_speed_limits': (4, 6)
    }
    mnist_testing_medium_params = {
        'data_dir': '../data/mnist',
        'split': 'testing',
        'color_output': False,
        'icon_labels': range(10),
        'position_speed_limits': (4, 6)
    }

    # Generalizing appearance, MNIST -> Icons8
    mnist_training_params = {
        'data_dir': '../data/mnist',
        'split': 'training',
        'color_output': False,
        'icon_labels': range(10),
        'position_speed_limits': (1, 9)
    }
    icons8_testing_params = {
        'data_dir': '../data/icons8',
        'split': 'testing',
        'color_output': False,
        'icon_labels': os.listdir('../data/icons8/training'),
        'position_speed_limits': (1, 9)
    }

    # Generalizing appearance, Icons8 -> MNIST
    icons8_training_params = {
        'data_dir': '../data/icons8',
        'split': 'training',
        'color_output': False,
        'icon_labels': os.listdir('../data/icons8/training'),
        'position_speed_limits': (1, 9)
    }
    mnist_testing_params = {
        'data_dir': '../data/mnist',
        'split': 'testing',
        'color_output': False,
        'icon_labels': range(10),
        'position_speed_limits': (1, 9)
    }

    training_dicts = {
        'mnist_training_slow': mnist_training_slow_params,
        'mnist_training_fast': mnist_training_fast_params,
        'mnist_training_slow_fast': mnist_training_slow_fast_params,
        'mnist_training_medium': mnist_training_medium_params,
        'mnist_training': mnist_training_params,
        'icons8_training': icons8_training_params
    }

    testing_dicts = {
        'mnist_testing_fast': mnist_testing_fast_params,
        'mnist_testing_medium': mnist_testing_medium_params,
        'icons8_testing': icons8_testing_params,
        'mnist_testing': mnist_testing_params
    }

    return training_dicts, testing_dicts


def generate_moving_icons_video((seed, num_frames, params)):
    """Create the T x H x W (x C) NumPy array for one video."""
    sub = MovingIconClassTrajectoryTracker()
    env = MovingIconEnvironment(params, seed, initial_subscribers=[sub])

    all_frames = []
    for i in xrange(num_frames):
        frame = env.next()
        all_frames.append(np.array(frame))
    video_tensor = np.array(all_frames, dtype=np.uint8)
    icon_classes, trajectories = sub.get_info()

    return video_tensor, icon_classes, trajectories


def generate_all_moving_icon_videos(pool, pool_seed, num_videos, num_frames, params,
                                    dataset_name):
    print('Working on %s...' % dataset_name)
    output_dir = os.path.join('..', 'output')
    arg_tups = [(seed, num_frames, params) for seed in xrange(pool_seed, pool_seed+num_videos)]
    # Get list of V TxHxW(xC) videos
    video_data = pool.map(generate_moving_icons_video, arg_tups)
    # video_data = map(generate_moving_icons_video, arg_tups)
    videos, icon_classes, trajectories = zip(*video_data)
    videos = np.stack(videos, axis=0)  # V x T x H x W (x C)
    icon_classes = np.stack(icon_classes, axis=0)  # V x D
    trajectories = np.stack(trajectories, axis=0)  # V x D x T x 2
    # Swap to bizarro Toronto dimensions (T x V x H x W (x C))
    videos = videos.swapaxes(0, 1)
    np.save(os.path.join(output_dir, '%s_videos.npy' % dataset_name), videos)
    np.save(os.path.join(output_dir, '%s_icon_classes.npy' % dataset_name), icon_classes)
    np.save(os.path.join(output_dir, '%s_trajectories.npy' % dataset_name), trajectories)


def main():
    pool_seed = 123
    num_training_videos = 10000
    num_training_frames = 20
    num_testing_videos = 1000
    num_testing_frames = 30

    pool = multiprocessing.Pool()
    training_params, testing_params = get_param_dicts()
    for dataset_name, params in training_params.iteritems():
        generate_all_moving_icon_videos(pool, pool_seed, num_training_videos, num_training_frames,
                                        params, dataset_name)
    for dataset_name, params in testing_params.iteritems():
        generate_all_moving_icon_videos(pool, pool_seed, num_testing_videos, num_testing_frames,
                                        params, dataset_name)

if __name__ == '__main__':
    main()