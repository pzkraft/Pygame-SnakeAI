import math
import pygame
import random
import collections
from enum import Enum
from collections import namedtuple
import numpy as np

pygame.init()
font = pygame.font.SysFont('monaco', 25)


class Direction(Enum):
    RIGHT = 1
    LEFT = 2
    UP = 3
    DOWN = 4


Point = namedtuple('Point', 'x, y')

# rgb colors
WHITE = (255, 255, 255)
RED = (200, 0, 0)
BLUE1 = (0, 0, 255)
BLUE2 = (0, 100, 255)
BLACK = (0, 0, 0)

BLOCK_SIZE = 20
SPEED = 400


class SnakeGameAI:
    # 640,480 160120
    def __init__(self, w=160, h=120):
        self.w = w
        self.h = h
        self.cols = self.w / BLOCK_SIZE
        self.rows = self.h / BLOCK_SIZE
        # init display
        self.display = pygame.display.set_mode((self.w, self.h))
        pygame.display.set_caption('Snake')
        self.clock = pygame.time.Clock()
        self.reset()
        self.dist = math.sqrt(
            (self.head.x - self.food.x) ** 2 + (self.head.y - self.food.y) ** 2)

    def reset(self):
        # init game state
        self.direction = Direction.RIGHT

        self.head = Point(self.w / 2, self.h / 2)
        self.snake = [self.head,
                      Point(self.head.x - BLOCK_SIZE, self.head.y),
                      Point(self.head.x - (2 * BLOCK_SIZE), self.head.y),
                      Point(self.head.x - (3 * BLOCK_SIZE), self.head.y)]

        self.score = 0
        self.food = None
        self._place_food()
        self.frame_iteration = 0
        self.idle_moves = 0

    def _place_food(self):
        x = random.randrange(0, int(self.w), BLOCK_SIZE)
        y = random.randrange(0, int(self.h), BLOCK_SIZE)
        self.food = Point(x, y)
        if self.food in self.snake:
            self._place_food()

    def _measure_distance(self):
        self.prev_dist = self.dist
        self.dist = math.sqrt(
            (self.head.x - self.food.x) ** 2 + (self.head.y - self.food.y) ** 2)

    def play_step(self, action):
        self.frame_iteration += 1
        # 1. collect user input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

        reward_given = False
        # 2. move
        self._move(action)  # update the head
        self.snake.insert(0, self.head)
        self._measure_distance()

        # 3. check if game over
        reward = 0
        game_over = False
        if self.is_collision() or self.frame_iteration > 100 * len(self.snake):
            game_over = True
            reward = -10
            print("Game over: Collision,", self.head)
            return reward, game_over, self.score

        if self.idle_moves > 100:
            game_over = True
            reward = -5
            print("Game over, Idle moves:", self.idle_moves, self.head)
            return reward, game_over, self.score

        # 4. place new food or just move
        if self.head == self.food:
            self.idle_moves = 0
            self.score += 1
            reward = 10
            reward_given = True
            self._place_food()
        else:
            self.snake.pop()

        # 5. motivation for snake to move more predictable
        if self.head.y == self.rows - 1:
            reward += 0.1

        if not reward_given:
            self.idle_moves += 1
            if self.dist < self.prev_dist:
                reward = 1
            else:
                reward = -1

        # 5. update ui and clock
        self._update_ui()
        self.clock.tick(SPEED)

        # 6. return game over and score
        return reward, game_over, self.score

    def is_collision(self, point=None):
        if point is None:
            point = self.head
        # hits boundary
        if point.x > self.w - BLOCK_SIZE or point.x < 0 or point.y > self.h - BLOCK_SIZE or point.y < 0:
            return True
        # hits itself
        if point in self.snake[1:]:
            return True

        return False

    def _update_ui(self):
        self.display.fill(BLACK)

        for point in self.snake:
            pygame.draw.rect(self.display, BLUE1, pygame.Rect(point.x, point.y, BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(self.display, BLUE2, pygame.Rect(point.x + 4, point.y + 4, 12, 12))

        pygame.draw.rect(self.display, RED, pygame.Rect(self.food.x, self.food.y, BLOCK_SIZE, BLOCK_SIZE))

        text_score = font.render("Score: " + str(self.score), True, WHITE)
        self.display.blit(text_score, [0, 0])
        pygame.display.flip()

    def _move(self, action):
        # [straight, right, left]

        clock_wise = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]
        idx = clock_wise.index(self.direction)

        if np.array_equal(action, [1, 0, 0]):
            new_dir = clock_wise[idx]  # no change
        elif np.array_equal(action, [0, 1, 0]):
            next_idx = (idx + 1) % 4
            new_dir = clock_wise[next_idx]  # right turn r -> d -> l -> u
        else:  # [0, 0, 1]
            next_idx = (idx - 1) % 4
            new_dir = clock_wise[next_idx]  # left turn r -> u -> l -> d

        self.direction = new_dir

        x = self.head.x
        y = self.head.y
        if self.direction == Direction.RIGHT:
            x += BLOCK_SIZE
        elif self.direction == Direction.LEFT:
            x -= BLOCK_SIZE
        elif self.direction == Direction.DOWN:
            y += BLOCK_SIZE
        elif self.direction == Direction.UP:
            y -= BLOCK_SIZE

        self.head = Point(x, y)

    def calc_open_spaces(self, start_pos):
        """Function to calculate the number of open spaces around the snake

        An open space is a space that the snake can reach without being blocked off by
        the wall or its own body.

        Arguments:
            start_pos: A tuple in (row,column) format representing a position of the snake's head

        Returns:
            An integer of how many open spaces are available.
        """
        open_spaces = 0
        start_x = start_pos[0]
        start_y = start_pos[1]
        snakebody_in_colsrows = list(map(lambda x: (x[0] / 20, x[1] / 20), self.snake))
        # If the start position is in the snake's body or out of bounds
        if start_pos in snakebody_in_colsrows or (
                start_x < 0 or start_x >= self.cols or start_y < 0 or start_y >= self.rows):
            # no open spaces
            return 0

        # Breadth first search is used
        # Create a set to represent th visited spaces
        visited = {start_pos}
        # Create a queue to keep track of which spaces need to be expanded
        queue = collections.deque([start_pos])
        # While there are still unvisited open spaces to search from
        while len(queue) > 0:

            cur = queue.popleft()
            possible_moves = self.get_possible_moves(cur)
            for move in possible_moves:
                if move not in visited:

                    visited.add(move)

                    # if the move is an open space
                    if move not in snakebody_in_colsrows:
                        open_spaces += 1
                        # add the open space to the queue for further searching
                        queue.append(move)
        return open_spaces

    def get_possible_moves(self, cur):
        """Function to get all the possible adjacent moves from a position.

        The function is called from calc_open_spaces() during the breadth first search.

        Arguments:
            cur: A tuple in (row,column) format representing the position
            to get the next possible moves from.

        Returns:
            A list containing (row,column) tuples of all the possible adjacent moves.
        """
        cur_x = cur[0]
        cur_y = cur[1]
        adjacent_spaces = [(cur_x, cur_y - 1), (cur_x - 1, cur_y),
                           (cur_x, cur_y + 1), (cur_x + 1, cur_y)]
        possible_moves = []
        for move in adjacent_spaces:
            move_x = move[0]
            move_y = move[1]
            # If the move is not out of bounds
            if 0 <= move_x < self.cols and 0 <= move_y < self.rows:
                possible_moves.append(move)
        return possible_moves
