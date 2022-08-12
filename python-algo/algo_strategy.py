import gamelib
import random
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

Y_MAX = 13
WALL_LENGTH = 20
TURRET_ORIGIN = [23, Y_MAX - 1]
TURRET_WALL_LOCATION = [TURRET_ORIGIN[0], TURRET_ORIGIN[1] + 1]
SUPPORT_ORIGIN = [16, 12]
SUPPORT_ROW_LENGTH = 5
SUPPORT_COST = 4
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
        self.prev_health = 30
        self.max_health_drop = 0

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(
            game_state.turn_number))
        # Comment or remove this line to enable warnings.
        game_state.suppress_warnings(True)

        # how much did our health decrease?
        curr_health = game_state.my_health
        self.max_health_drop = max(
            self.max_health_drop, self.prev_health - curr_health)

        # BASE SPAWN
        # horizontal wall
        for x in range(WALL_LENGTH):
            game_state.attempt_spawn(WALL, [x, Y_MAX])

        # turret diagonal
        num_turrets = 2
        for i in range(num_turrets):
            game_state.attempt_spawn(
                TURRET, [TURRET_ORIGIN[0] - i, TURRET_ORIGIN[1] - i])

        # protective wall for turret
        game_state.attempt_spawn(WALL, TURRET_WALL_LOCATION)
        game_state.attempt_upgrade(TURRET_WALL_LOCATION)

        # protective wall on right edge
        for i in range(num_turrets + 3):
            right_wall_location = [TURRET_ORIGIN[0] +
                                   4 - i, TURRET_ORIGIN[1] + 1 - i]
            game_state.attempt_spawn(WALL, right_wall_location)
            if (i < num_turrets):
                game_state.attempt_upgrade(right_wall_location)

        # OPTIONAL SPAWNS
        # wall upgrades
        wall_upgrade_count = 3
        for x in range(wall_upgrade_count):
            game_state.attempt_upgrade([WALL_LENGTH - x, Y_MAX])
        wall_upgrade_count += 1

        # last stand: change thresholds for spawning/upgrading resources based on current
        # health
        support_cost, scout_cost = SUPPORT_COST, MP_THRESHOLD_SCOUT
        if curr_health <= self.max_health_drop:
            support_cost, scout_cost = 0, 0

        # supports
        if (game_state.get_resource(SP) > support_cost):
            support_location = [
                SUPPORT_ORIGIN[0] + (self.support_count % SUPPORT_ROW_LENGTH), SUPPORT_ORIGIN[1]]
            game_state.attempt_spawn(SUPPORT, support_location)
            game_state.attempt_upgrade(support_location)
            self.support_count += 1

        # UNIT SPAWN
        # scout swarm
        if (game_state.get_resource(MP) > scout_cost):
            game_state.attempt_spawn(
                SCOUT, SCOUT_SPAWN_LOCATION, int(game_state.get_resource(MP)))

        self.prev_health = curr_health
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
                gamelib.debug_write(
                    "All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
