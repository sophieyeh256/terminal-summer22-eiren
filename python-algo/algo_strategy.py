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
        # Fixed Variables
        self.WALL = self.config["unitInformation"][0]["shorthand"]
        self.SUPPORT = self.config["unitInformation"][1]["shorthand"]
        self.TURRET = self.config["unitInformation"][2]["shorthand"]
        self.SCOUT = self.config["unitInformation"][3]["shorthand"]
        self.DEMOLISHER = self.config["unitInformation"][4]["shorthand"]
        self.INTERCEPTOR = self.config["unitInformation"][5]["shorthand"]
        self.MP = 1
        self.SP = 0
        self.Y_MAX = 13
        self.X_MAX = 27
        self.WALL_LENGTH = 20
        self.TURRET_ORIGIN = [23, self.Y_MAX - 1]
        self.TURRET_WALL_LOCATION = [self.TURRET_ORIGIN[0], self.TURRET_ORIGIN[1] + 1]
        self.SUPPORT_ORIGIN = [16, 12]
        self.SUPPORT_ROW_LENGTH = 5
        self.MP_THRESHOLD_SCOUT = 10
        self.SUPPORT_COST = self.config["unitInformation"][1]["cost1"]
        self.LEFT = 'LEFT'
        self.RIGHT = 'RIGHT'
        # wall distances
        self.OUTPOST_WALL_X_DISTANCES = [0, 4, 8]
        self.OUTPOST_WALL_Y = self.Y_MAX
        self.HORIZONTAL_WALL_X_DISTANCE = 9
        self.HORIZONTAL_WALL_Y = self.OUTPOST_WALL_Y - 1
        self.HORIZONTAL_WALL_LENGTH = 5
        self.TURRET_ORIGIN_X_DISTANCE = 4
        self.TURRET_ORIGIN_Y = self.OUTPOST_WALL_Y - 1
        self.NUM_STARTING_TURRETS = 1
        self.TURRET_LIMIT = 4
        self.BLOCK_WALL_ORIGIN_X_DISTANCE = 1
        self.BLOCK_WALL_ORIGIN_Y = self.TURRET_ORIGIN_Y
        self.BLOCK_WALL_LENGTH = 7
        self.SUPPORT_ORIGIN_X_DISTANCE = 9
        self.SUPPORT_ORIGIN_Y = self.BLOCK_WALL_ORIGIN_Y - 1
        self.SUPPORT_ROW_LENGTH = 4
        self.SUPPORT_LIMIT = 24
        # Modifiable variables
        self.SCOUT_SPAWN_LOCATION = [[13, 0]]
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.support_count = 0
        self.support_row = 0
        self.prev_health = 30
        self.max_health_drop = 0
        self.curr_turret_count = 0

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.

        Destroyer crawl if the entrance is blocked
        (if you send the destroyer on the fourth row horizontally,
        it will be at max range to destroy the enemy structures on their first row)
        Check if entrance is heavily guarded and spawn a lot of destroyers

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

        ## main walls
        for x_distance in self.OUTPOST_WALL_X_DISTANCES:
            self.spawn_symmetrically(game_state, self.WALL, x_distance, self.OUTPOST_WALL_Y)
            self.upgrade_symmetrically(game_state, x_distance, self.OUTPOST_WALL_Y)

        for horizontal_wall_count in range(self.HORIZONTAL_WALL_LENGTH):
            self.spawn_symmetrically(game_state, self.WALL, self.HORIZONTAL_WALL_X_DISTANCE + horizontal_wall_count, self.HORIZONTAL_WALL_Y)

        prev_sp_count = game_state.get_resource(self.SP)
        for num_turret in range(self.NUM_STARTING_TURRETS):
            self.spawn_symmetrically(game_state, self.TURRET, self.TURRET_ORIGIN_X_DISTANCE + num_turret, self.TURRET_ORIGIN_Y - num_turret)
            self.spawn_symmetrically(game_state, self.WALL, num_turret + 1, self.TURRET_ORIGIN_Y - num_turret)
            self.upgrade_symmetrically(game_state, num_turret + 1, self.TURRET_ORIGIN_Y - num_turret)

        if (prev_sp_count - game_state.get_resource(self.SP) > 0):
            self.curr_turret_count = min(self.TURRET_LIMIT, self.curr_turret_count + 1)

        # Close one side
        def choose_left_side_to_block():
            return True

        if (game_state.turn_number == 1):
            if (choose_left_side_to_block()):
                self.blocked_side = self.LEFT
                self.opened_side = self.RIGHT
            else:
                self.blocked_side = self.RIGHT
                self.opened_side = self.LEFT

        if (game_state.turn_number >= 1):
            for block_wall_count in range(self.BLOCK_WALL_LENGTH):
                self.spawn(game_state, self.WALL, self.BLOCK_WALL_ORIGIN_X_DISTANCE + block_wall_count, self.BLOCK_WALL_ORIGIN_Y, self.blocked_side)

            for num_turret in range(self.curr_turret_count):
                self.spawn(game_state, self.TURRET, self.TURRET_ORIGIN_X_DISTANCE + num_turret, self.TURRET_ORIGIN_Y - num_turret, self.opened_side)
                self.spawn(game_state, self.WALL, num_turret + 1, self.TURRET_ORIGIN_Y - num_turret, self.opened_side)
                self.upgrade(game_state, num_turret + 1, self.TURRET_ORIGIN_Y - num_turret, self.opened_side)

            num_supports = 0
            while(game_state.get_resource(self.SP) > self.SUPPORT_COST and num_supports < self.SUPPORT_LIMIT):
                self.spawn(game_state, self.SUPPORT, self.SUPPORT_ORIGIN_X_DISTANCE + (num_supports % self.SUPPORT_ROW_LENGTH), self.SUPPORT_ORIGIN_Y - (num_supports // self.SUPPORT_ROW_LENGTH), self.opened_side)
                self.upgrade(game_state, self.SUPPORT_ORIGIN_X_DISTANCE + (num_supports % self.SUPPORT_ROW_LENGTH), self.SUPPORT_ORIGIN_Y - (num_supports // self.SUPPORT_ROW_LENGTH), self.opened_side)
                num_supports += 1

        # last stand: change thresholds for spawning/upgrading resources based on current
        # health
        support_threshold, scout_threshold = self.SUPPORT_COST, self.MP_THRESHOLD_SCOUT
        if curr_health <= self.max_health_drop:
            support_threshold, scout_threshold = 0, 0

        # supports -- SHOULD THIS BE DELETED?
        if (game_state.get_resource(self.SP) > support_threshold):
            support_location = [
                self.SUPPORT_ORIGIN[0] + (self.support_count % self.SUPPORT_ROW_LENGTH), self.SUPPORT_ORIGIN[1]]
            game_state.attempt_spawn(self.WALL, support_location)
            game_state.attempt_upgrade(support_location)
            self.support_count += 1

        # MOBILE UNIT SPAWN
        if game_state.turn_number == 0:
            # Two interceptors to patrol along wall
            patrol_locations = [[6,7], [21,7]]
            game_state.attempt_spawn(self.DEMOLISHER, patrol_locations[0], 1)
            game_state.attempt_spawn(self.INTERCEPTOR, patrol_locations[1], 1)
        elif game_state.turn_number > 0:
            # After updated state
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                self.demolisher_line_strategy(game_state)
            # Removes any locations that are blocked by structures
            self.SCOUT_SPAWN_LOCATION = self.filter_blocked_locations(self.SCOUT_SPAWN_LOCATION, game_state)
            # Determines which side has least damage from structures from potential self.SCOUT_SPAWN_LOCATIONs
            self.SCOUT_SPAWN_LOCATION, damage = self.least_damage_spawn_location(game_state, self.SCOUT_SPAWN_LOCATION)
            scout_health = game_state.get_resource(self.MP)*self.config["unitInformation"][3]["startHealth"]
            # Deploy demolishers until scouts can sustain damage from enemy structures
            if damage > scout_health:
                num_demolishers = int(math.ceil((damage - scout_health) // self.config["unitInformation"][4]["startHealth"]))
                game_state.attempt_spawn(self.DEMOLISHER, self.SCOUT_SPAWN_LOCATION, num_demolishers)
            # Deploy scouts with remaining self.MP only if scouts can sustain damage
            if damage < scout_health or num_demolishers*self.config["unitInformation"][4]["cost2"] < game_state.get_resource(self.MP):
                game_state.attempt_spawn(self.SCOUT, self.SCOUT_SPAWN_LOCATION, int(game_state.get_resource(self.MP)))

        self.prev_health = curr_health
        game_state.submit_turn()

    def spawn(self, game_state, structure_type, x, y, side):
        if (side == self.LEFT):
            game_state.attempt_spawn(structure_type, [x, y])
        else:
            game_state.attempt_spawn(structure_type, [self.X_MAX - x, y])

    def upgrade(self, game_state, x, y, side):
        if (side == self.LEFT):
            game_state.attempt_upgrade([x, y])
        else:
            game_state.attempt_upgrade([self.X_MAX - x, y])

    def spawn_symmetrically(self, game_state, structure_type, x, y):
        self.spawn(game_state, structure_type, x, y, self.LEFT)
        self.spawn(game_state, structure_type, x, y, self.RIGHT)

    def upgrade_symmetrically(self, game_state, x, y):
        self.upgrade(game_state, x, y, self.LEFT)
        self.upgrade(game_state, x, y, self.RIGHT)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(self.TURRET, game_state.config).damage_i
            damages.append(damage)

        # Now just return the location that takes the least damage and the damage
        return [location_options[damages.index(min(damages))]], min(damages)

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered
    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(self.DEMOLISHER, [24, 10], 1)
    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units

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
