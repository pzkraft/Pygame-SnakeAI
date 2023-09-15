
import torch
import random
import numpy as np
from collections import deque
from game import SnakeGameAI, Direction, Point
from model import Linear_QNet, QTrainer
from helper import plot

MAX_MEMORY = 1_000_000
BATCH_SIZE = 1000
LR = 0.001


class Agent:

    def __init__(self):
        self.n_games = 0
        self.epsilon = 0  # randomness
        self.gamma = 0.9  # discount rate
        self.memory = deque(maxlen=MAX_MEMORY)  # popleft()
        self.model = Linear_QNet(11, 256, 3)
        self.trainer = QTrainer(self.model, lr=LR, gamma=self.gamma)

    def get_state(self, game):
        head = game.snake[0]
        # get nearby points in cols and rows
        point_l = Point(head.x / 20 - 1, head.y / 20)
        point_r = Point(head.x / 20 + 1, head.y / 20)
        point_u = Point(head.x / 20, head.y / 20 - 1)
        point_d = Point(head.x / 20, head.y / 20 + 1)

        dir_l = game.direction == Direction.LEFT
        dir_r = game.direction == Direction.RIGHT
        dir_u = game.direction == Direction.UP
        dir_d = game.direction == Direction.DOWN

        const = (game.rows * game.cols) - len(game.snake) / (game.rows * game.cols)
        open_spaces_left = game.calc_open_spaces(point_l) / const
        open_spaces_up = game.calc_open_spaces(point_u) / const
        open_spaces_right = game.calc_open_spaces(point_r) / const
        open_spaces_down = game.calc_open_spaces(point_d) / const

        # transform open_spaces values to True of False
        if (open_spaces_left == max([open_spaces_left, open_spaces_up, open_spaces_right, open_spaces_down])
                and open_spaces_left != 0):
            os_l = True
        else:
            os_l = False

        if (open_spaces_up == max([open_spaces_left, open_spaces_up, open_spaces_right, open_spaces_down])
                and open_spaces_up != 0):
            os_u = True
        else:
            os_u = False

        if (open_spaces_right == max([open_spaces_left, open_spaces_up, open_spaces_right, open_spaces_down])
                and open_spaces_right != 0):
            os_r = True
        else:
            os_r = False

        if (open_spaces_down == max([open_spaces_left, open_spaces_up, open_spaces_right, open_spaces_down])
                and open_spaces_down != 0):
            os_d = True
        else:
            os_d = False

        state = [

            # Danger straight
            (dir_r and not os_r) or
            (dir_l and not os_l) or
            (dir_u and not os_u) or
            (dir_d and not os_d),

            # Danger right
            (dir_u and not os_r) or
            (dir_d and not os_l) or
            (dir_l and not os_u) or
            (dir_r and not os_d),

            # Danger left
            (dir_d and not os_r) or
            (dir_u and not os_l) or
            (dir_r and not os_u) or
            (dir_l and not os_d),

            # Move direction
            dir_l,
            dir_r,
            dir_u,
            dir_d,

            # Food location
            game.food.x < game.head.x,  # food left
            game.food.x > game.head.x,  # food right
            game.food.y < game.head.y,  # food up
            game.food.y > game.head.y  # food down
        ]

        return np.array(state, dtype=int)

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))  # popleft if MAX_MEMORY is reached

    def train_long_memory(self):
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE)  # list of tuples
        else:
            mini_sample = self.memory

        states, actions, rewards, next_states, dones = zip(*mini_sample)
        self.trainer.train_step(states, actions, rewards, next_states, dones)
        # for state, action, reward, nexrt_state, done in mini_sample:
        #    self.trainer.train_step(state, action, reward, next_state, done)

    def train_short_memory(self, state, action, reward, next_state, done):
        self.trainer.train_step(state, action, reward, next_state, done)

    def get_action(self, state):
        # random moves: tradeoff exploration / exploitation
        self.epsilon = 80 - self.n_games
        final_move = [0, 0, 0]
        if random.randint(0, 200) < self.epsilon:
            move = random.randint(0, 2)
            final_move[move] = 1
        else:
            state0 = torch.tensor(state, dtype=torch.float)
            prediction = self.model(state0)
            move = torch.argmax(prediction).item()
            final_move[move] = 1

        return final_move


def train():
    plot_scores = []
    plot_mean_scores = []
    total_score = 0
    record = 0
    agent = Agent()
    game = SnakeGameAI()
    while True:
        # get old state
        state_old = agent.get_state(game)

        # get move
        final_move = agent.get_action(state_old)

        # perform move and get new state
        reward, done, score = game.play_step(final_move)
        state_new = agent.get_state(game)

        # train short memory
        agent.train_short_memory(state_old, final_move, reward, state_new, done)

        # remember
        agent.remember(state_old, final_move, reward, state_new, done)

        if done:
            # train long memory, plot result
            game.reset()
            agent.n_games += 1
            agent.train_long_memory()

            if score > record:
                record = score
                agent.model.save()

            print('Game', agent.n_games, 'Score', score, 'Record:', record)

            plot_scores.append(score)
            total_score += score
            mean_score = total_score / agent.n_games
            plot_mean_scores.append(mean_score)
            plot(plot_scores, plot_mean_scores)


if __name__ == '__main__':
    train()
