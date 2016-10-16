import math
from .Var import Var, VarType


known_types = []


class Entity:

    @staticmethod
    def _from_raw(type, vars, rotation, layer, unk2, unk3, unk4):
        for class_type in known_types:
            if type == class_type.TYPE_IDENTIFIER:
                return class_type(vars, rotation, layer, unk2, unk3, unk4)
        entity = Entity(vars, rotation, layer, unk2, unk3, unk4)
        entity.type = type
        return entity

    def __init__(self, vars=None, rotation=0,
                 layer=18, unk2=1, unk3=1, unk4=1):
        if hasattr(self, "TYPE_IDENTIFIER"):
            self.type = self.TYPE_IDENTIFIER
        self.vars = {} if vars is None else vars
        self.rotation = rotation
        self.layer = layer
        self.unk2 = unk2
        self.unk3 = unk3
        self.unk4 = unk4

    def __repr__(self):
        return "Entity: (%s, %d, %d, %d, %d, %d, %s)" % (
            self.type, self.rotation, self.layer, self.unk2, self.unk3,
            self.unk4, repr(self.vars))

    def remap_ids(self, id_map):
        pass

    def transform(self, mat):
        angle = math.atan2(mat[1][1], mat[1][0]) - math.pi / 2
        self.rotation = self.rotation - \
            int(0x10000 * angle / math.pi / 2) & 0xFFFF

        if mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0] < 0:
            self.unk3 = 1 - self.unk3
            self.rotation = -self.rotation & 0xFFFF


class TriggerArea(Entity):

    def __init__(self, vars, rotation=0,
                 layer=0, unk2=0, unk3=0, unk4=0):
        if 'trigger_area' not in vars:
            vars['trigger_area'] = Var(VarType.ARRAY, (VarType.VEC2, []))
        super(TriggerArea, self).__init__(
            vars, rotation, layer, unk2, unk3, unk4)

    def area_count(self):
        return len(self.vars['trigger_area'].value[1])

    def area_position(self, ind, val=None):
        result = self.vars['trigger_area'].value[1][ind].value
        if val is not None:
            self.vars['trigger_area'].value[1][ind] = Var(VarType.VEC2, val)
        return result

    def area_append(self, val):
        self.vars['trigger_area'].value[1].append(Var(VarType.VEC2, val))

    def area_pop(self, ind=None):
        return self.vars['trigger_area'].value[1].pop(ind).value

    def area_clear(self):
        self.vars['trigger_area'].value[1] = []

    def transform(self, mat):
        for i in range(self.area_count()):
            pos = self.area_position(i)
            self.area_position(i,
                               (pos[0] * mat[0][0] + pos[1] * mat[0][1],
                                pos[0] * mat[1][0] + pos[1] * mat[1][1]))
        super(TriggerArea, self).transform(mat)


class CheckPoint(TriggerArea):
    TYPE_IDENTIFIER = "check_point"

known_types.append(CheckPoint)


class EndZone(TriggerArea):
    TYPE_IDENTIFIER = "level_end_prox"

known_types.append(EndZone)


class Trigger(Entity):

    def __init__(self, vars, rotation=0,
                 layer=0, unk2=0, unk3=0, unk4=0):
        if 'width' not in vars:
            vars['width'] = Var(VarType.UINT, 500)
        super(Trigger, self).__init__(vars, rotation, layer, unk2, unk3, unk4)


class FogTrigger(Trigger):
    TYPE_IDENTIFIER = "fog_trigger"

known_types.append(FogTrigger)


class DeathZone(Entity):
    TYPE_IDENTIFIER = "kill_box"

    def __init__(self, vars, rotation=0,
                 layer=0, unk2=0, unk3=0, unk4=0):
        if 'width' not in vars:
            vars['width'] = Var(VarType.INT, 1)
        if 'height' not in vars:
            vars['height'] = Var(VarType.INT, 1)
        super(DeathZone, self).__init__(
            vars, rotation, layer, unk2, unk3, unk4)

    def width(self, val=None):
        result = self.vars['width'].value / 48.0
        if val is not None:
            self.vars['width'].value = round(val * 48)
        return result

    def height(self, val=None):
        result = self.vars['height'].value / 48.0
        if val is not None:
            self.vars['height'].value = round(val * 48)
        return result

    def transform(self, mat):
        width = self.width()
        height = self.height()
        self.width(abs(width * mat[0][0] + height * mat[0][1]))
        self.height(abs(width * mat[1][0] + height * mat[1][1]))
        super(DeathZone, self).transform(mat)

known_types.append(DeathZone)


class AIController(Entity):
    TYPE_IDENTIFIER = "AI_controller"

    def __init__(self, vars, rotation=0,
                 layer=0, unk2=0, unk3=0, unk4=0):
        if 'puppet_id' not in vars:
            vars['puppet_id'] = Var(VarType.INT, 0)
        if 'nodes' not in vars:
            vars['nodes'] = Var(VarType.ARRAY, (VarType.VEC2, []))
        super(AIController, self).__init__(
            vars, rotation, layer, unk2, unk3, unk4)

    def puppet(self, val=None):
        result = self.vars['puppet_id'].value
        if val is not None:
            self.vars['puppet_id'].value = val
        return result

    def node_count(self):
        return len(self.vars['nodes'].value[1])

    def node_position(self, ind, val=None):
        result = self.vars['nodes'].value[1][ind].value
        if val is not None:
            self.vars['nodes'].value[1][ind] = Var(VarType.VEC2,
                                                   (val[0] * 48, val[1] * 48))
        return (result[0] / 48, result[1] / 48)

    def node_append(self, val):
        self.vars['nodes'].value[1].append(Var(VarType.VEC2,
                                               (val[0] * 48, val[1] * 48)))

    def node_pop(self, ind=None):
        return self.vars['nodes'].value[1].pop(ind).value

    def node_clear(self):
        self.vars['nodes'].value[1] = []

    def remap_ids(self, id_map):
        if self.puppet() in id_map:
            self.puppet(id_map[self.puppet()])
        else:
            self.puppet(-1)

    def transform(self, mat):
        for i in range(self.node_count()):
            pos = self.node_position(i)
            self.node_position(
                i,
                (mat[0][2] + pos[0] * mat[0][0] + pos[1] * mat[0][1],
                 mat[1][2] + pos[0] * mat[1][0] + pos[1] * mat[1][1])
            )
        super(AIController, self).transform(mat)

known_types.append(AIController)


class CameraNode(Entity):
    TYPE_IDENTIFIER = "camera_node"

    def __init__(self, vars, rotation=0,
                 layer=0, unk2=0, unk3=0, unk4=0):
        if 'c_node_ids' not in vars:
            vars['c_node_ids'] = Var(VarType.ARRAY, (VarType.INT, []))
        super(CameraNode, self).__init__(
            vars, rotation, layer, unk2, unk3, unk4)

    def connection_count(self):
        return len(self.vars['c_node_ids'].value[1])

    def connection(self, ind, val=None):
        result = self.vars['c_node_ids'].value[1][ind].value
        if val is not None:
            self.vars['c_node_ids'].value[1][ind] = Var(VarType.INT, val)
        return result

    def connection_append(self, val):
        self.vars['c_node_ids'].value[1].append(Var(VarType.INT, val))

    def connection_pop(self, ind=None):
        return self.vars['c_node_ids'].value[1].pop(ind).value

    def connection_clear(self):
        self.vars['c_node_ids'].value = (VarType.INT, [])

    def remap_ids(self, id_map):
        for i in range(self.connection_count()):
            self.connection(i, id_map[self.connection(i)])

known_types.append(CameraNode)


class LevelEnd(Entity):
    TYPE_IDENTIFIER = "level_end"

    def __init__(self, vars, rotation=0,
                 layer=0, unk2=0, unk3=0, unk4=0):
        if 'ent_list' not in vars:
            vars['ent_list'] = Var(VarType.ARRAY, (VarType.INT, []))
        super(LevelEnd, self).__init__(vars, rotation, layer, unk2, unk3, unk4)

    def entity_count(self):
        return len(self.vars['ent_list'].value[1])

    def entity(self, ind, val=None):
        result = self.vars['ent_list'].value[1][ind].value
        if val is not None:
            self.vars['ent_list'].value[1][ind] = Var(VarType.INT, val)
        return result

    def entity_append(self, val):
        self.vars['ent_list'].value[1].append(Var(VarType.INT, val))

    def entity_pop(self, ind=None):
        return self.vars['ent_list'].value[1].pop(ind).value

    def entity_clear(self):
        self.vars['ent_list'].value[1] = []

    def remap_ids(self, id_map):
        for i in range(self.entity_count()):
            self.entity(i, id_map[self.entity(i)])

known_types.append(LevelEnd)


class Enemy(Entity):

    def __init__(self, vars=None, rotation=0, layer=18, unk2=1,
                 unk3=1, unk4=1):
        super(Enemy, self).__init__(vars, rotation, layer, unk2, unk3, unk4)

    def filth(self):
        return 1

    def combo(self):
        return self.filth()


class EnemyLightPrism(Enemy):
    TYPE_IDENTIFIER = "enemy_tutorial_square"


class EnemyHeavyPrism(Enemy):
    TYPE_IDENTIFIER = "enemy_tutorial_hexagon"

    def combo(self):
        return 3


class EnemySlimeBeast(Enemy):
    TYPE_IDENTIFIER = "enemy_slime_beast"

    def filth(self):
        return 9


class EnemySlimeBarrel(Enemy):
    TYPE_IDENTIFIER = "enemy_slime_barrel"

    def filth(self):
        return 3


class EnemySpringBall(Enemy):
    TYPE_IDENTIFIER = "enemy_spring_ball"

    def filth(self):
        return 5


class EnemySlimeBall(Enemy):
    TYPE_IDENTIFIER = "enemy_slime_ball"

    def filth(self):
        return 3


class EnemyTrashTire(Enemy):
    TYPE_IDENTIFIER = "enemy_trash_tire"

    def filth(self):
        return 3


class EnemyTrashBeast(Enemy):
    TYPE_IDENTIFIER = "enemy_trash_beast"

    def filth(self):
        return 9


class EnemyTrashCan(Enemy):
    TYPE_IDENTIFIER = "enemy_trash_can"

    def filth(self):
        return 9


class EnemyTrashBall(Enemy):
    TYPE_IDENTIFIER = "enemy_trash_ball"

    def filth(self):
        return 3


class EnemyBear(Enemy):
    TYPE_IDENTIFIER = "enemy_bear"

    def filth(self):
        return 9


class EnemyTotemLarge(Enemy):
    TYPE_IDENTIFIER = "enemy_stoneboss"

    def filth(self):
        return 12


class EnemyTotemSmall(Enemy):
    TYPE_IDENTIFIER = "enemy_stonebro"

    def filth(self):
        return 3


class EnemyPorcupine(Enemy):
    TYPE_IDENTIFIER = "enemy_porcupine"


class EnemyWolf(Enemy):
    TYPE_IDENTIFIER = "enemy_wolf"

    def filth(self):
        return 5


class EnemyTurkey(Enemy):
    TYPE_IDENTIFIER = "enemy_critter"

    def filth(self):
        return 3


class EnemyFlag(Enemy):
    TYPE_IDENTIFIER = "enemy_flag"

    def filth(self):
        return 5


class EnemyScroll(Enemy):
    TYPE_IDENTIFIER = "enemy_scrolls"


class EnemyTreasure(Enemy):
    TYPE_IDENTIFIER = "enemy_treasure"


class EnemyChestTreasure(Enemy):
    TYPE_IDENTIFIER = "enemy_chest_treasure"

    def filth(self):
        return 9


class EnemyChestScrolls(Enemy):
    TYPE_IDENTIFIER = "enemy_chest_scrolls"

    def filth(self):
        return 9


class EnemyButler(Enemy):
    TYPE_IDENTIFIER = "enemy_butler"


class EnemyMaid(Enemy):
    TYPE_IDENTIFIER = "enemy_maid"


class EnemyKnight(Enemy):
    TYPE_IDENTIFIER = "enemy_knight"

    def filth(self):
        return 9


class EnemyGargoyleBig(Enemy):
    TYPE_IDENTIFIER = "enemy_gargoyle_big"

    def filth(self):
        return 5


class EnemyGargoyleSmall(Enemy):
    TYPE_IDENTIFIER = "enemy_gargoyle_small"

    def filth(self):
        return 3


class EnemyBook(Enemy):
    TYPE_IDENTIFIER = "enemy_book"

    def filth(self):
        return 3


class EnemyHawk(Enemy):
    TYPE_IDENTIFIER = "enemy_hawk"

    def filth(self):
        return 3


known_types.append(EnemyLightPrism)
known_types.append(EnemyHeavyPrism)
known_types.append(EnemySlimeBeast)
known_types.append(EnemySlimeBarrel)
known_types.append(EnemySpringBall)
known_types.append(EnemySlimeBall)
known_types.append(EnemyTrashTire)
known_types.append(EnemyTrashBeast)
known_types.append(EnemyTrashCan)
known_types.append(EnemyTrashBall)
known_types.append(EnemyBear)
known_types.append(EnemyTotemLarge)
known_types.append(EnemyTotemSmall)
known_types.append(EnemyPorcupine)
known_types.append(EnemyWolf)
known_types.append(EnemyTurkey)
known_types.append(EnemyFlag)
known_types.append(EnemyScroll)
known_types.append(EnemyTreasure)
known_types.append(EnemyChestTreasure)
known_types.append(EnemyChestScrolls)
known_types.append(EnemyButler)
known_types.append(EnemyMaid)
known_types.append(EnemyKnight)
known_types.append(EnemyGargoyleBig)
known_types.append(EnemyGargoyleSmall)
known_types.append(EnemyBook)
known_types.append(EnemyHawk)


class Apple(Entity):
    TYPE_IDENTIFIER = "hittable_apple"


class Dustman(Entity):
    TYPE_IDENTIFIER = "dust_man"


class Dustgirl(Entity):
    TYPE_IDENTIFIER = "dust_girl"


class Dustkid(Entity):
    TYPE_IDENTIFIER = "dust_kid"


class Dustworth(Entity):
    TYPE_IDENTIFIER = "dust_worth"


class Dustwraith(Entity):
    TYPE_IDENTIFIER = "dust_wraith"


class Leafsprite(Entity):
    TYPE_IDENTIFIER = "leaf_sprite"


class Trashking(Entity):
    TYPE_IDENTIFIER = "trash_king"


class Slimeboss(Entity):
    TYPE_IDENTIFIER = "slime_boss"


known_types.append(Apple)
known_types.append(Dustman)
known_types.append(Dustgirl)
known_types.append(Dustkid)
known_types.append(Dustworth)
known_types.append(Dustwraith)
known_types.append(Leafsprite)
known_types.append(Trashking)
known_types.append(Slimeboss)
