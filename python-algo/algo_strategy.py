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
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.support_count = 0
        self.support_row = 0

        # Fixed Variables
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, Y_MAX, WALL_LENGTH, TURRET_ORIGIN, TURRET_WALL_LOCATION,SUPPORT_ORIGIN, SUPPORT_ROW_LENGTH, SUPPORT_COST
        WALL = self.config["unitInformation"][0]["shorthand"]
        SUPPORT = self.config["unitInformation"][1]["shorthand"]
        TURRET = self.config["unitInformation"][2]["shorthand"]
        SCOUT = self.config["unitInformation"][3]["shorthand"]
        DEMOLISHER = self.config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = self.config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        Y_MAX = 13
        WALL_LENGTH = 20
        TURRET_ORIGIN = [23, Y_MAX - 1]
        TURRET_WALL_LOCATION = [TURRET_ORIGIN[0], TURRET_ORIGIN[1] + 1]
        SUPPORT_ORIGIN = [16, 12]
        SUPPORT_ROW_LENGTH = 5
        SUPPORT_COST = self.config["unitInformation"][1]["cost1"]
        # MP_THRESHOLD_SCOUT = 10 # SY: currently not being used

        # Modifiable variables
        self.SCOUT_SPAWN_LOCATION = [[13, 0]]



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
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        # BASE SPAWN
        # horizontal wall
        for x in range(WALL_LENGTH):
            game_state.attempt_spawn(WALL, [x, Y_MAX])

        # turret diagonal
        num_turrets = 2
        for i in range(num_turrets):
            game_state.attempt_spawn(TURRET, [TURRET_ORIGIN[0] - i, TURRET_ORIGIN[1] - i])

        # protective wall for turret
        game_state.attempt_spawn(WALL, TURRET_WALL_LOCATION)
        game_state.attempt_upgrade(TURRET_WALL_LOCATION)

        # protective wall on right edge
        for i in range(num_turrets + 3):
            right_wall_location = [TURRET_ORIGIN[0] + 4 - i, TURRET_ORIGIN[1] + 1 - i]
            game_state.attempt_spawn(WALL, right_wall_location)
            if (i < num_turrets):
                game_state.attempt_upgrade(right_wall_location)
        # OPTIONAL SPAWNS
        # wall upgrades
        wall_upgrade_count = 3
        for x in range(wall_upgrade_count):
            game_state.attempt_upgrade([WALL_LENGTH - x, Y_MAX])
        wall_upgrade_count += 1

        # supports
        if (game_state.get_resource(SP) > SUPPORT_COST):
            support_location = [SUPPORT_ORIGIN[0] + (self.support_count % SUPPORT_ROW_LENGTH), SUPPORT_ORIGIN[1]]
            game_state.attempt_spawn(SUPPORT, support_location)
            game_state.attempt_upgrade(support_location)
            self.support_count += 1

        # MOBILE UNIT SPAWN
        if game_state.turn_number == 0:
            # Two interceptors to patrol along wall
            patrol_locations = [[6,7], [21,7]]
            game_state.attempt_spawn(DEMOLISHER, patrol_locations[0], 1)
            game_state.attempt_spawn(INTERCEPTOR, patrol_locations[1], 1)
        elif game_state.turn_number > 0:
            # After updated state
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                self.demolisher_line_strategy(game_state)
            # Removes any locations that are blocked by structures
            self.SCOUT_SPAWN_LOCATION = self.filter_blocked_locations(self.SCOUT_SPAWN_LOCATION, game_state)
            # Determines which side has least damage from structures from potential self.SCOUT_SPAWN_LOCATIONs
            self.SCOUT_SPAWN_LOCATION, damage = self.least_damage_spawn_location(game_state, self.SCOUT_SPAWN_LOCATION)
            scout_health = game_state.get_resource(MP)*self.config["unitInformation"][3]["startHealth"]
            # Deploy demolishers until scouts can sustain damage from enemy structures
            if damage > scout_health:
                num_demolishers = int(math.ceil((damage - scout_health) // self.config["unitInformation"][4]["startHealth"]))
                game_state.attempt_spawn(DEMOLISHER, self.SCOUT_SPAWN_LOCATION, num_demolishers)
            # Deploy scouts with remaining MP only if scouts can sustain damage
            if damage < scout_health or num_demolishers*self.config["unitInformation"][4]["cost2"] < game_state.get_resource(MP):
                game_state.attempt_spawn(SCOUT, self.SCOUT_SPAWN_LOCATION, int(game_state.get_resource(MP)))

        game_state.submit_turn()


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
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
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
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 1)
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
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
