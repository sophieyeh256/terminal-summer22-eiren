import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips:

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical
  board states. Though, we recommended making a copy of the map to preserve
  the actual current map state.
"""

LEFT = 'LEFT'
RIGHT = 'RIGHT'

X_MAX = 27
Y_MAX = 13

OUTPOST_WALL_X_DISTANCES = [0, 4, 8]
OUTPOST_WALL_Y = Y_MAX

HORIZONTAL_WALL_X_DISTANCE = 9
HORIZONTAL_WALL_Y = OUTPOST_WALL_Y - 1
HORIZONTAL_WALL_LENGTH = 5

TURRET_ORIGIN_X_DISTANCE = 4
TURRET_ORIGIN_Y = OUTPOST_WALL_Y - 1
NUM_STARTING_TURRETS = 1
TURRET_LIMIT = 4

BLOCK_WALL_ORIGIN_X_DISTANCE = 1
BLOCK_WALL_ORIGIN_Y = TURRET_ORIGIN_Y
BLOCK_WALL_LENGTH = 7

SUPPORT_ORIGIN_X_DISTANCE = 9
SUPPORT_ORIGIN_Y = BLOCK_WALL_ORIGIN_Y - 1
SUPPORT_ROW_LENGTH = 4
SUPPORT_COST = 6
SUPPORT_LIMIT = 24

MP_THRESHOLD_SCOUT = 10
SCOUT_SPAWN_LOCATION = [13, 0]

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """
        Read in config and perform any initial setup here
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.support_count = 0
        self.support_row = 0
        self.curr_turret_count = NUM_STARTING_TURRETS
        self.blocked_side = None
        self.opened_side = None

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        # BASE SPAWN
        ## main walls
        def spawn(structure_type, x, y, side = LEFT):
            if (side == LEFT):
                game_state.attempt_spawn(structure_type, [x, y])
            else:
                game_state.attempt_spawn(structure_type, [X_MAX - x, y])

        def upgrade(x, y, side = LEFT):
            if (side == LEFT):
                game_state.attempt_upgrade([x, y])
            else:
                game_state.attempt_upgrade([X_MAX - x, y])

        def spawn_symmetrically(structure_type, x, y):
            spawn(structure_type, x, y, LEFT)
            spawn(structure_type, x, y, RIGHT)

        def upgrade_symmetrically(x, y):
            upgrade(x, y, LEFT)
            upgrade(x, y, RIGHT)

        for x_distance in OUTPOST_WALL_X_DISTANCES:
            spawn_symmetrically(WALL, x_distance, OUTPOST_WALL_Y)
            upgrade_symmetrically(x_distance, OUTPOST_WALL_Y)

        for horizontal_wall_count in range(HORIZONTAL_WALL_LENGTH):
            spawn_symmetrically(WALL, HORIZONTAL_WALL_X_DISTANCE + horizontal_wall_count, HORIZONTAL_WALL_Y)

        prev_sp_count = game_state.get_resource(SP)
        for num_turret in range(NUM_STARTING_TURRETS):
            spawn_symmetrically(TURRET, TURRET_ORIGIN_X_DISTANCE + num_turret, TURRET_ORIGIN_Y - num_turret)
            spawn_symmetrically(WALL, num_turret + 1, TURRET_ORIGIN_Y - num_turret)
            upgrade_symmetrically(num_turret + 1, TURRET_ORIGIN_Y - num_turret)

        if (prev_sp_count - game_state.get_resource(SP) > 0):
            self.curr_turret_count = min(TURRET_LIMIT, self.curr_turret_count + 1)

        # Close one side
        def choose_left_side_to_block():
            return True

        if (game_state.turn_number == 1):
            if (choose_left_side_to_block()):
                self.blocked_side = LEFT
                self.opened_side = RIGHT
            else:
                self.blocked_side = RIGHT
                self.opened_side = LEFT

        if (game_state.turn_number >= 1):
            for block_wall_count in range(BLOCK_WALL_LENGTH):
                spawn(WALL, BLOCK_WALL_ORIGIN_X_DISTANCE + block_wall_count, BLOCK_WALL_ORIGIN_Y, self.blocked_side)

            for num_turret in range(self.curr_turret_count):
                spawn(TURRET, TURRET_ORIGIN_X_DISTANCE + num_turret, TURRET_ORIGIN_Y - num_turret, self.opened_side)
                spawn(WALL, num_turret + 1, TURRET_ORIGIN_Y - num_turret, self.opened_side)
                upgrade(num_turret + 1, TURRET_ORIGIN_Y - num_turret, self.opened_side)

            num_supports = 0
            while(game_state.get_resource(SP) > SUPPORT_COST and num_supports < SUPPORT_LIMIT):
                spawn(SUPPORT, SUPPORT_ORIGIN_X_DISTANCE + (num_supports % SUPPORT_ROW_LENGTH), SUPPORT_ORIGIN_Y - (num_supports // SUPPORT_ROW_LENGTH), self.opened_side)
                upgrade(SUPPORT_ORIGIN_X_DISTANCE + (num_supports % SUPPORT_ROW_LENGTH), SUPPORT_ORIGIN_Y - (num_supports // SUPPORT_ROW_LENGTH), self.opened_side)
                num_supports += 1

        # UNIT SPAWN
        # scout swarm
        if (game_state.get_resource(MP) > MP_THRESHOLD_SCOUT):
            game_state.attempt_spawn(SCOUT, SCOUT_SPAWN_LOCATION, int(game_state.get_resource(MP)))

        game_state.submit_turn()

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
