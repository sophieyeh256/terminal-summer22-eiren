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

        Y_MAX = 13
        # BASE SPAWN
        # horizontal wall
        WALL_LENGTH = 19
        for x in range(WALL_LENGTH):
            game_state.attempt_spawn(WALL, [x, Y_MAX])

        # turret diagonal
        TURRET_ORIGIN = [23, Y_MAX - 1]
        num_turrets = 2
        for i in range(num_turrets):
            game_state.attempt_spawn(TURRET, [TURRET_ORIGIN[0] - i, TURRET_ORIGIN[1] - i])

        # protective wall for turret
        TURRET_WALL_LOCATION = [TURRET_ORIGIN[0], TURRET_ORIGIN[1] + 1]
        game_state.attempt_spawn(WALL, TURRET_WALL_LOCATION)
        game_state.attempt_upgrade(TURRET_WALL_LOCATION)

        # protective wall on right edge
        for i in range(num_turrets + 3):
            right_wall_location = [TURRET_ORIGIN[0] + 3 - i, TURRET_ORIGIN[1] + 1 - i]
            game_state.attempt_spawn(WALL, right_wall_location)
            game_state.attempt_upgrade(right_wall_location)

        # OPTIONAL SPAWNS
        # wall upgrades
        wall_upgrade_count = 3
        for x in range(wall_upgrade_count):
            game_state.attempt_upgrade([WALL_LENGTH - x, Y_MAX])
        wall_upgrade_count += 1

        # supports
        SUPPORT_ORIGIN = [14, 12]
        SUPPORT_ROW_LENGTH = 6
        SUPPORT_COST = 6
        support_count = 0
        location = SUPPORT_ORIGIN
        if (game_state.get_resource(SP) > SUPPORT_COST):
            game_state.attempt_spawn(SUPPORT, location)
            game_state.attempt_upgrade(location)
            count += 1
            location = [location[0] + (support_count % SUPPORT_ROW_LENGTH), location[1] + (support_count // SUPPORT_ROW_LENGTH)]

        # UNIT SPAWN
        # scout swarm
        MP_THRESHOLD = 10
        SCOUT_SPAWN_LOCATION = [13, 0]
        if (game_state.get_resource(MP) > MP_THRESHOLD):
            game_state.attempt_spawn(SCOUT, SCOUT_SPAWN_LOCATION, int(game_state.get_resource(MP)))

        game_state.submit_turn()

    # def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
    #     total_units = 0
    #     for location in game_state.game_map:
    #         if game_state.contains_stationary_unit(location):
    #             for unit in game_state.game_map[location]:
    #                 if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
    #                     total_units += 1
    #     return total_units
    #
    # def filter_blocked_locations(self, locations, game_state):
    #     filtered = []
    #     for location in locations:
    #         if not game_state.contains_stationary_unit(location):
    #             filtered.append(location)
    #     return filtered

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
