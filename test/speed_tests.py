import time, sys

sys.argv.append("-nb")
from nidac_importer import Nidac

code = """
# ==============================================================================
# NIDAVELLIR COMPREHENSIVE BENCHMARK SUITE
# ==============================================================================

class Vector2:
    def void __init__(self, float x, float y):
        self.x = x
        self.y = y

    def float get_x(self):
        return self.x

    def float get_y(self):
        return self.y

    def void set_x(self, float x):
        self.x = x

    def void set_y(self, float y):
        self.y = y

    def void add(self, Vector2 other):
        self.x = self.x + other.get_x()
        self.y = self.y + other.get_y()


class Transform:
    def void __init__(self, float x, float y):
        self.position = Vector2(x, y)
        self.scale = Vector2(1.0, 1.0)

    def Vector2 get_position(self):
        return self.position

    def Vector2 get_scale(self):
        return self.scale

    def void translate(self, float dx, float dy):
        offset = Vector2(dx, dy)
        self.position.add(offset)


class HealthComponent:
    def void __init__(self, int max_hp):
        self.max_hp = max_hp
        self.current_hp = max_hp

    def int get_hp(self):
        return self.current_hp

    def int is_alive(self):
        if self.current_hp > 0:
            return 1
        else:
            return 0

    def void take_damage(self, int amount):
        self.current_hp = self.current_hp - amount
        if self.current_hp < 0:
            self.current_hp = 0

    def void heal(self, int amount):
        self.current_hp = self.current_hp + amount
        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp


class AttributeSet:
    def void __init__(self, int str_val, int agi_val, int int_val):
        self.strength = str_val
        self.agility = agi_val
        self.intelligence = int_val

    def int get_strength(self):
        return self.strength

    def int get_agility(self):
        return self.agility

    def int get_intelligence(self):
        return self.intelligence

    def void add_strength(self, int val):
        self.strength = self.strength + val


class ItemSlot:
    def void __init__(self, int item_id, int count):
        self.item_id = item_id
        self.count = count

    def int get_id(self):
        return self.item_id

    def int get_count(self):
        return self.count

    def void add_count(self, int amount):
        self.count = self.count + amount


class Inventory:
    def void __init__(self, int capacity):
        self.capacity = capacity
        self.slot1 = ItemSlot(101, 1)
        self.slot2 = ItemSlot(102, 5)
        self.item_count = 2

    def ItemSlot get_slot1(self):
        return self.slot1

    def ItemSlot get_slot2(self):
        return self.slot2

    def int get_total_items(self):
        c1 = self.slot1.get_count()
        c2 = self.slot2.get_count()
        return c1 + c2


class GameObject:
    def void __init__(self, int object_id, float x, float y, int hp):
        self.object_id = object_id
        self.transform = Transform(x, y)
        self.health = HealthComponent(hp)

    def Transform get_transform(self):
        return self.transform

    def HealthComponent get_health(self):
        return self.health

    def int get_id(self):
        return self.object_id


class Player:
    def void __init__(self, int player_id, float x, float y):
        self.base_obj = GameObject(player_id, x, y, 100)
        self.attributes = AttributeSet(10, 8, 5)
        self.inventory = Inventory(20)
        self.level = 1

    def GameObject get_base(self):
        return self.base_obj

    def AttributeSet get_attributes(self):
        return self.attributes

    def Inventory get_inventory(self):
        return self.inventory

    def int get_level(self):
        return self.level

    def void level_up(self):
        self.level = self.level + 1
        self.attributes.add_strength(2)
        health = self.base_obj.get_health()
        health.heal(20)


class Enemy:
    def void __init__(self, int enemy_id, float x, float y, int attack):
        self.base_obj = GameObject(enemy_id, x, y, 50)
        self.attack_power = attack

    def GameObject get_base(self):
        return self.base_obj

    def int get_attack(self):
        return self.attack_power


class BattleManager:
    def void __init__(self, Player player, Enemy enemy):
        self.player = player
        self.enemy = enemy

    def int execute_turn(self):
        p_base = self.player.get_base()
        p_health = p_base.get_health()

        e_base = self.enemy.get_base()
        e_health = e_base.get_health()

        p_alive = p_health.is_alive()
        e_alive = e_health.is_alive()

        if p_alive == 1:
            if e_alive == 1:
                p_attrs = self.player.get_attributes()
                damage = p_attrs.get_strength()
                e_health.take_damage(damage)

        e_still_alive = e_health.is_alive()
        if e_still_alive == 0:
            self.player.level_up()
            return 1

        if e_still_alive == 1:
            enemy_dmg = self.enemy.get_attack()
            p_health.take_damage(enemy_dmg)

        p_still_alive = p_health.is_alive()
        if p_still_alive == 0:
            return 2

        return 0


class GameWorld:
    def void __init__(self):
        self.player = Player(1, 0.0, 0.0)
        self.enemy = Enemy(2, 2.0, 2.0, 8)

    def Player get_player(self):
        return self.player

    def void run_simulation(self):
        p_base = self.player.get_base()
        p_trans = p_base.get_transform()
        p_trans.translate(1.0, 1.0)

        battle = BattleManager(self.player, self.enemy)
        status = 0

        while status == 0:
            status = battle.execute_turn()


def void main():
    world = GameWorld()
    world.run_simulation()

    player = world.get_player()
    p_base = player.get_base()
    p_health = p_base.get_health()

    final_hp = p_health.get_hp()
    final_level = player.get_level()

    inv = player.get_inventory()
    total_items = inv.get_total_items()
"""
code = """
def test(a, b):
    return b


test(1, 2)
"""
top_t1 = time.perf_counter()

import builtins

_original_print = builtins.print


def my_custom_print(*args, **kwargs):
    force = kwargs.pop("force", False)
    if not force:
        return

    _original_print(*args, **kwargs)


builtins.print = my_custom_print


test_count = 200
latencys = []

for _ in range(test_count):
    t1 = time.perf_counter()

    nida = Nidac(source=code)
    nida.compile()

    t2 = time.perf_counter()

    latency = t2 - t1
    latencys.append(latency)

top_t2 = time.perf_counter()

average_latency = sum(latencys) / len(latencys)
min_latency = min(latencys)
max_latency = max(latencys)

total_time = top_t2 - top_t1
processed_lines = len(code.splitlines()) * test_count

print(f"Average Latency: {average_latency * 1000:.2f} ms", force=True)
print(f"Min Latency: {min_latency * 1000:.2f} ms", force=True)
print(f"Max Latency: {max_latency * 1000:.2f} ms", force=True)
print(
    f"Total Time: {total_time}\n" f"Processed Lines of Code: {processed_lines}",
    force=True,
)
print(f"Lines per second: {processed_lines / total_time:.2f}", force=True)
