import pygame
import random
import collections
from enum import Enum
from collections import namedtuple
import numpy as np

pygame.init()
font = pygame.font.SysFont('monaco', 25)


# font = pygame.font.SysFont('arial', 25)

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

    def __init__(self, w=640, h=480):
        self.w = w
        self.h = h
        # init display
        self.display = pygame.display.set_mode((self.w, self.h))
        pygame.display.set_caption('Snake')
        self.clock = pygame.time.Clock()
        self.reset()

    def reset(self):
        # init game state
        self.direction = Direction.RIGHT

        self.head = Point(self.w / 2, self.h / 2)
        self.snake = [self.head,
                      Point(self.head.x - BLOCK_SIZE, self.head.y),
                      Point(self.head.x - (2 * BLOCK_SIZE), self.head.y)]

        self.score = 0
        self.food = None
        self._place_food()
        self.frame_iteration = 0

    def _place_food(self):
        x = random.randint(0, (self.w - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE
        y = random.randint(0, (self.h - BLOCK_SIZE) // BLOCK_SIZE) * BLOCK_SIZE
        self.food = Point(x, y)
        if self.food in self.snake:
            self._place_food()

    def play_step(self, action):
        self.frame_iteration += 1
        # 1. collect user input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

        # 2. move
        self._move(action)  # update the head
        self.snake.insert(0, self.head)

        # 3. check if game over
        reward = 0
        game_over = False
        if self.is_collision() or self.frame_iteration > 100 * len(self.snake):
            game_over = True
            reward = -10
            return reward, game_over, self.score

        # 4. place new food or just move
        if self.head == self.food:
            self.score += 1
            reward = 10
            self._place_food()
        else:
            self.snake.pop()

        # 5. update ui and clock
        self._update_ui()
        self.clock.tick(SPEED)
        # 6. return game over and score
        return reward, game_over, self.score

    def is_collision(self, pt=None):
        if pt is None:
            pt = self.head
        # hits boundary
        if pt.x > self.w - BLOCK_SIZE or pt.x < 0 or pt.y > self.h - BLOCK_SIZE or pt.y < 0:
            return True
        # hits itself
        if pt in self.snake[1:]:
            return True

        return False

    def _update_ui(self):
        self.display.fill(BLACK)

        for pt in self.snake:
            pygame.draw.rect(self.display, BLUE1, pygame.Rect(pt.x, pt.y, BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(self.display, BLUE2, pygame.Rect(pt.x + 4, pt.y + 4, 12, 12))

        pygame.draw.rect(self.display, RED, pygame.Rect(self.food.x, self.food.y, BLOCK_SIZE, BLOCK_SIZE))

        text = font.render("Score: " + str(self.score), True, WHITE)
        self.display.blit(text, [0, 0])
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

    def _calc_open_spaces(self, start_pos):
        """Function to calculate the number of open spaces around the snake

        An open space is a space that the snake can reach without being blocked off by
        the wall or its own body.

        Arguments:
            start_pos: A tuple in (row,column) format representing a position of the snake's head

        Returns:
            An integer of how many open spaces are available.
        """
        open_spaces = 0

        start_y = start_pos.y
        start_x = start_pos.x

        # If the start position is in the snake's body or out of bounds
        if start_pos in self.snake[1:] or (
                start_x < 0 or start_x >= self.w or start_y < 0 or start_y >= self.h):
            # no open spaces
            return 0

        # Breadth first search is used

        # Create a set to represent th visited spaces
        visited = {start_pos}
        # Create a queue to keep track of which spaces need to be expanded
        queue = collections.deque((start_y, start_x))

        # While there are still unvisited open spaces to search from
        while len(queue) > 0:

            cur = queue.popleft()

            possible_moves = self._get_possible_moves(cur)

            for move in possible_moves:
                if move not in visited:

                    visited.add(move)

                    # if the move is an open space
                    if move not in self.snake[1:]:
                        open_spaces += 1
                        # add the open space to the queue for further searching
                        queue.append(move)

        return open_spaces

    def _get_possible_moves(self, cur):
        """Function to get all the possible adjacent moves from a position.

        The function is called from calc_open_spaces() during the breadth first search.

        Arguments:
            cur: A tuple in (row,column) format representing the position
            to get the next possible moves from.

        Returns:
            A list containing (row,column) tuples of all the possible adjacent moves.
        """
        point_y = int(cur.y)
        point_x = int(cur.x)
        adjacent_spaces = [(point_y, point_x - 1), (point_y - 1, point_x),
                           (point_y, point_x + 1), (point_y + 1, point_x)]
        possible_moves = []
        for move in adjacent_spaces:
            move_y = move[1]
            move_x = move[0]
            # If the move is not out of bounds
            if 0 <= move_x < self.w and 0 <= move_y < self.h:
                possible_moves.append(move)
        return possible_moves
