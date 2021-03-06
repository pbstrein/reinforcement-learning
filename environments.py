from copy import copy
import gym
import holodeck
from holodeck.sensors import Sensors
import numpy as np
import vizdoom as vzd

from rl import EnvironmentFactory
from rl import RLEnvironment


class CartPoleEnvironmentFactory(EnvironmentFactory):
    def __init__(self):
        super(CartPoleEnvironmentFactory, self).__init__()

    def new(self):
        return CartPoleEnvironment()


class CartPoleEnvironment(RLEnvironment):
    def __init__(self):
        super(CartPoleEnvironment, self).__init__()
        self._env = gym.make('CartPole-v0')

    def step(self, action):
        """action is type np.ndarray of shape [1] and type np.uint8.
        Returns observation (np.ndarray), r (float), t (boolean)
        """
        s, r, t, _ = self._env.step(action.item())
        return s, r, t

    def reset(self):
        """Returns observation (np.ndarray)"""
        return self._env.reset()


class DoomHallwayFactory(EnvironmentFactory):
    def __init__(self):
        super(DoomHallwayFactory, self).__init__()

    def new(self):
        return DoomHallwayEnvironment()


class DoomHallwayEnvironment(RLEnvironment):
    def __init__(self, prev_frames=4, skiprate=1):
        super(DoomHallwayEnvironment, self).__init__()
        self._res = (120, 160)
        self._prev_frames = prev_frames
        self._skiprate = skiprate
        self._imgs = np.zeros((self._res[0], self._res[1], prev_frames), dtype=np.float32)

        self._game = vzd.DoomGame()
        self._game.set_doom_scenario_path('scenarios/deadly_corridor.wad')
        self._game.set_doom_map("map01")
        self._game.set_screen_resolution(vzd.ScreenResolution.RES_160X120)
        self._game.set_screen_format(vzd.ScreenFormat.RGB24)
        self._game.set_living_reward(0.0)
        self._game.set_doom_skill(5)

        self._game.add_available_button(vzd.Button.ATTACK)
        self._game.add_available_button(vzd.Button.MOVE_FORWARD)
        self._game.add_available_button(vzd.Button.MOVE_LEFT)
        self._game.add_available_button(vzd.Button.MOVE_RIGHT)
        self._game.add_available_button(vzd.Button.TURN_LEFT)
        self._game.add_available_button(vzd.Button.TURN_RIGHT)

        self._game.set_episode_timeout(3000)
        self._game.set_episode_start_time(10)
        self._game.set_window_visible(False)

        self._game.init()
        self._actions = [
            [True, False, False, False, False, False],
            [False, True, False, False, False, False],
            [False, False, True, False, False, False],
            [False, False, False, True, False, False],
            [False, False, False, False, True, False],
            [False, False, False, False, False, True],
        ]

    def step(self, action):
        action = action.item()
        r = self._game.make_action(self._actions[action], self._skiprate)
        # r = float(max(min(r, 1.0), -1.0))  # Clamp r to between -1 and 1
        r = float(r)

        t = self._game.is_episode_finished()

        if t:
            return self._imgs, -1.0, t

        state = self._game.get_state()
        screen_buf = state.screen_buffer
        self._process_state(screen_buf)

        if type(r) != float:
            print(type(r), r)
        return self._imgs, r, t

    def reset(self):
        self._imgs = np.zeros((self._res[0], self._res[1], self._prev_frames), dtype=np.float32)
        self._game.new_episode()
        state = self._game.get_state()
        screen_buf = state.screen_buffer
        self._process_state(screen_buf)
        return self._imgs

    def _process_state(self, s):
        self._imgs = np.roll(self._imgs, 1, axis=2)
        self._imgs[:, :, 0] = np.mean(s.astype(np.float32) / 255, axis=2)


class MazeWorldEnvironmentFactory(EnvironmentFactory):
    def __init__(self):
        super(MazeWorldEnvironmentFactory, self).__init__()

    def new(self):
        return MazeWorldEnvironment()


class MazeWorldEnvironment(RLEnvironment):
    def __init__(self, res=(128, 128), prev_frames=4):
        super(MazeWorldEnvironment, self).__init__()
        self._env = holodeck.make('MazeWorld', window_res=(256, 256), cam_res=res)
        self._res = res
        self._prev_frames = prev_frames
        self._imgs = np.zeros((res[0], res[1], prev_frames), dtype=np.float32)
        self._interval = 1.0
        self._next_interval = self._interval

    def step(self, action):
        s, _, _, _ = self._env.step(action.item())

        r = 0.0
        if s[Sensors.LOCATION_SENSOR][0] >= self._next_interval:
            r += 1
            self._next_interval += self._interval

        self._process_state(s)
        return self._imgs, r, False

    def reset(self):
        self._imgs = np.zeros((self._res[0], self._res[1], self._prev_frames), dtype=np.float32)
        s, _, _, _ = self._env.reset()
        self._process_state(s)
        self._next_interval = self._interval
        return self._imgs

    def _process_state(self, s):
        self._imgs = np.roll(self._imgs, 1, axis=2)
        self._imgs[:, :, 0] = np.mean(copy(s[Sensors.RGB_CAMERA][:, :, :3]).astype(np.float32) / 255, axis=2)
