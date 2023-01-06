#-*-coding:GBK -*-
#2022202210046-�����
#2022202210057-������

import copy
from itertools import product
from matplotlib import pyplot as plt
from mpl_toolkits import mplot3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import time

from numpy.core.shape_base import _block

# ���Ͽ����С�����
MIN_FILL_RATE = 0.8
# ���з��þ�������Ӧ���Ͽ鶥������ȵ���Сֵ
MIN_AREA_RATE = 0.8
# ���Ͽ�����Ӷ�
MAX_TIMES = 2
# ���������
MAX_DEPTH = 3
# �������ڵ��֧��
MAX_BRANCH = 2

# ��ʱ�����ŷ��÷���
tmp_best_ps = None


# ջ���ݽṹ�����ڴ洢ʣ��ռ�
class Stack:
    def __init__(self):
        self.data = []

    def empty(self):
        return len(self.data) == 0

    def not_empty(self):
        return len(self.data) > 0

    def pop(self):
        return self.data.pop() if len(self.data) > 0 else None

    def push(self, *items):
        for item in items:
            self.data.append(item)

    def top(self):
        return self.data[len(self.data) - 1] if len(self.data) > 0 else None

    def clear(self):
        self.data.clear()

    def size(self):
        return len(self.data)


# ������
class Box:
    def __init__(self, lx, ly, lz, type=0):
        # ��
        self.lx = lx
        # ��
        self.ly = ly
        # ��
        self.lz = lz
        # ����
        self.type = type

    def __str__(self):
        return "lx: {}, ly: {}, lz: {}, type: {}".format(self.lx, self.ly, self.lz, self.type)


# ʣ��ռ���
class Space:
    def __init__(self, x, y, z, lx, ly, lz, origin=None):
        # ����
        self.x = x
        self.y = y
        self.z = z
        # ��
        self.lx = lx
        # ��
        self.ly = ly
        # ��
        self.lz = lz
        # ��ʾ���ĸ�ʣ��ռ��и����
        self.origin = origin

    def __str__(self):
        return "x:{},y:{},z:{},lx:{},ly:{},lz:{}".format(self.x, self.y, self.z, self.lx, self.ly, self.lz)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z and self.lx == other.lx and self.ly == other.ly and self.lz == other.lz


# װ��������
class Problem:
    def __init__(self, container: Space, box_list=[], num_list=[]):
        # ����
        self.container = container
        # �����б�
        self.box_list = box_list
        # ���Ӷ�Ӧ������
        self.num_list = num_list


# ����
class Block:
    def __init__(self, lx, ly, lz, require_list=[], children=[], direction=None):
        # ��
        self.lx = lx
        # ��
        self.ly = ly
        # ��
        self.lz = lz
        # ��Ҫ����Ʒ����
        self.require_list = require_list
        # ���
        self.volume = 0
        # �ӿ��б��򵥿���ӿ��б�Ϊ��
        self.children = children
        # ���Ͽ��ӿ�ĺϲ�����
        self.direction = direction
        # �����ɷ��þ��γߴ�
        self.ax = 0
        self.ay = 0
        # ���Ӷȣ����ϴ���
        self.times = 0
        # ��Ӧ�ȣ���ѡ��ʱʹ��
        self.fitness = 0

    def __str__(self):
        return "lx: %s, ly: %s, lz: %s, volume: %s, ax: %s, ay: %s, times:%s, fitness: %s, require: %s, children: " \
               "%s, direction: %s" % (self.lx, self.ly, self.lz, self.volume, self.ax, self.ay, self.times, self.fitness, self.require_list, self.children, self.direction)

    def __eq__(self, other):
        return self.lx == other.lx and self.ly == other.ly and self.lz == other.lz and self.ax == other.ax and self.ay == self.ay and (np.array(self.require_list) == np.array(other.require_list)).all()

    def __hash__(self):
        return hash(",".join([str(self.lx), str(self.ly), str(self.lz), str(self.ax), str(self.ay), ",".join([str(r) for r in self.require_list])]))


# ������
class Place:
    def __init__(self, space: Space, block: Block):
        # �ռ�
        self.space = space
        # ��
        self.block = block

    def __eq__(self, other):
        return self.space == other.space and self.block == other.block


# װ��״̬��
class PackingState:
    def __init__(self, plan_list=[], space_stack: Stack = Stack(), avail_list=[]):
        # �����ɵ�װ�䷽���б�
        self.plan_list = plan_list
        # ʣ��ռ��ջ
        self.space_stack = space_stack
        # ʣ�������������
        self.avail_list = avail_list
        # ��װ����Ʒ�����
        self.volume = 0
        # ����װ����Ʒ�������������ֵ
        self.volume_complete = 0


# �ϲ���ʱͨ��У����Ŀ
def combine_common_check(combine: Block, container: Space, num_list):
    # �Ϲ���ߴ粻�ô��������ߴ�
    if combine.lx > container.lx:
        return False
    if combine.ly > container.ly:
        return False
    if combine.lz > container.lz:
        return False
    # �Ϲ�����Ҫ�������������ô��������ܵ�����
    if (np.array(combine.require_list) > np.array(num_list)).any():
        return False
    # �ϲ��������������С����С�����
    if combine.volume / (combine.lx * combine.ly * combine.lz) < MIN_FILL_RATE:
        return False
    # �ϲ���Ķ����ɷ��þ��α����㹻��
    if (combine.ax * combine.ay) / (combine.lx * combine.ly) < MIN_AREA_RATE:
        return False
    # �ϲ���ĸ��ӶȲ��ó�������Ӷ�
    if combine.times > MAX_TIMES:
        return False
    return True


# �ϲ���ʱͨ�úϲ���Ŀ
def combine_common(a: Block, b: Block, combine: Block):
    # �ϲ����������������
    combine.require_list = (np.array(a.require_list) + np.array(b.require_list)).tolist()
    # �ϲ�������
    combine.volume = a.volume + b.volume
    # �������ӹ�ϵ
    combine.children = [a, b]
    # �ϲ���ĸ��Ӷ�
    combine.times = max(a.times, b.times) + 1


# ���ɼ򵥿�
def gen_simple_block(container, box_list, num_list):
    block_table = []
    for box in box_list:
        for nx in np.arange(num_list[box.type]) + 1:
            for ny in np.arange(num_list[box.type] / nx) + 1:
                for nz in np.arange(num_list[box.type] / nx / ny) + 1:
                    if box.lx * nx <= container.lx and box.ly * ny <= container.ly and box.lz * nz <= container.lz:
                        # xy���Եߵ� ֱ���������block
                        # �ü򵥿���Ҫ��������������
                        requires = np.full_like(num_list, 0)
                        requires[box.type] = nx * ny * nz
                        # �򵥿�
                        block1 = Block(box.lx * nx, box.ly * ny, box.lz * nz, requires)
                        block2 = Block(box.ly * nx, box.lx * ny, box.lz * nz, requires)
                        # �����ɷ��þ���
                        block1.ax = box.lx * nx
                        block1.ay = box.ly * ny
                        block2.ax = box.ly * nx
                        block2.ay = box.lx * ny
                        # �򵥿�������
                        block1.volume = box.lx * nx * box.ly * ny * box.lz * nz
                        block2.volume = box.lx * nx * box.ly * ny * box.lz * nz
                        # �򵥿鸴�Ӷ�
                        block1.times = 0
                        block2.times = 0
                        block_table.append(block1)
                        block_table.append(block2)
    return sorted(block_table, key=lambda x: x.volume, reverse=True)


# ���ɸ��Ͽ�
def gen_complex_block(container, box_list, num_list):
    # �����ɼ򵥿�
    block_table = gen_simple_block(container, box_list, num_list)
    for times in range(MAX_TIMES):
        new_block_table = []
        # ѭ�����м򵥿飬�������
        for i in np.arange(0, len(block_table)):
            # ��һ���򵥿�
            a = block_table[i]
            for j in np.arange(0, len(block_table)):
                # �򵥿鲻���Լ�����
                if j == i:
                    continue
                # �ڶ����򵥿�
                b = block_table[j]
                # ���Ӷ����㵱ǰ���Ӷ�
                if a.times == times or b.times == times:
                    c = Block(0, 0, 0)
                    # ��x�᷽�򸴺�
                    if a.ax == a.lx and b.ax == b.lx and a.lz == b.lz:
                        c.direction = "x"
                        c.ax = a.ax + b.ax
                        c.ay = min(a.ay, b.ay)
                        c.lx = a.lx + b.lx
                        c.ly = max(a.ly, b.ly)
                        c.lz = a.lz
                        combine_common(a, b, c)
                        if combine_common_check(c, container, num_list):
                            new_block_table.append(c)
                            continue
                    # ��y�᷽�򸴺�
                    if a.ay == a.ly and b.ay == b.ly and a.lz == b.lz:
                        c.direction = "y"
                        c.ax = min(a.ax, b.ax)
                        c.ay = a.ay + b.ay
                        c.lx = max(a.lx, b.lx)
                        c.ly = a.ly + b.ly
                        c.lz = a.lz
                        combine_common(a, b, c)
                        if combine_common_check(c, container, num_list):
                            new_block_table.append(c)
                            continue
                    # ��z�᷽�򸴺�
                    if a.ax >= b.lx and a.ay >= b.ly:
                        c.direction = "z"
                        c.ax = b.ax
                        c.ay = b.ay
                        c.lx = a.lx
                        c.ly = a.ly
                        c.lz = a.lz + b.lz
                        combine_common(a, b, c)
                        if combine_common_check(c, container, num_list):
                            new_block_table.append(c)
                            continue
        # ���������ɵĸ��Ͽ�
        block_table = block_table + new_block_table
        # ȥ�أ�ӵ����ͬ���߳��ȡ���Ʒ����Ͷ����ɷ��þ��εĸ��Ͽ鱻��Ϊ�ȼۿ飬�ظ����ɵĵȼۿ齫������
        block_table = list(set(block_table))
    # ���������Ը��Ͽ��������
    return sorted(block_table, key=lambda x: x.volume, reverse=True)


# ���ɿ��п��б�
def gen_block_list(space: Space, avail, block_table):
    block_list = []
    for block in block_table:
        # ������Ҫ������������������С�ڵ�ǰ��װ�����������
        # ��ĳߴ����С�ڷ��ÿռ�ߴ�
        if (np.array(block.require_list) <= np.array(avail)).all() and \
                block.lx <= space.lx and block.ly <= space.ly and block.lz <= space.lz:
            block_list.append(block)
    return block_list


# ���г��µ�ʣ��ռ䣨���ȶ���Լ����
def gen_residual_space(space: Space, block: Block, box_list=[]):
    # ����ά�ȵ�ʣ��ߴ�
    rmx = space.lx - block.lx
    rmy = space.ly - block.ly
    rmz = space.lz - block.lz
    # �����²��г���ʣ��ռ䣨����ջ˳�����η��أ�
    if rmx >= rmy:
        # ��ת�ƿռ������x���и�ռ�
        drs_x = Space(space.x + block.lx, space.y, space.z, rmx, space.ly, space.lz, space)
        drs_y = Space(space.x, space.y + block.ly, space.z, block.lx, rmy, space.lz, space)
        drs_z = Space(space.x, space.y, space.z + block.lz, block.ax, block.ay, rmz, None)
        return drs_z, drs_y, drs_x
    else:
        # ��ת�ƿռ������y���и�ռ�
        drs_x = Space(space.x + block.lx, space.y, space.z, rmx, block.ly, space.lz, space)
        drs_y = Space(space.x, space.y + block.ly, space.z, space.lx, rmy, space.lz, space)
        drs_z = Space(space.x, space.y, space.z + block.lz, block.ax, block.ay, rmz, None)
        return drs_z, drs_x, drs_y


# �ռ�ת��
def transfer_space(space: Space, space_stack: Stack):
    # ��ʣһ���ռ�Ļ���ֱ�ӵ���
    if space_stack.size() <= 1:
        space_stack.pop()
        return None
    # ��ת�ƿռ��ԭʼ�ռ�
    discard = space
    # Ŀ��ռ�
    space_stack.pop()
    target = space_stack.top()
    # ����ת�ƵĿռ�ת�Ƹ�Ŀ��ռ�
    if discard.origin is not None and target.origin is not None and discard.origin == target.origin:
        new_target = copy.deepcopy(target)
        # ��ת�ƿռ�ԭ�ȹ�����y���и�ռ�����
        if discard.lx == discard.origin.lx:
            new_target.ly = discard.origin.ly
        # ��ת�ƿռ�ԭ��������x���и�ռ�����
        elif discard.ly == discard.origin.ly:
            new_target.lx = discard.origin.lx
        else:
            return None
        space_stack.pop()
        space_stack.push(new_target)
        # ����δ����ת��֮ǰ��Ŀ��ռ�
        return target
    return None


# ��ԭ�ռ�ת��
def transfer_space_back(space: Space, space_stack: Stack, revert_space: Space):
    space_stack.pop()
    space_stack.push(revert_space)
    space_stack.push(space)


# ������㷨
def place_block(ps: PackingState, block: Block):
    # ջ��ʣ��ռ�
    space = ps.space_stack.pop()
    # ���¿���������Ŀ
    ps.avail_list = (np.array(ps.avail_list) - np.array(block.require_list)).tolist()
    # ���·��üƻ�
    place = Place(space, block)
    ps.plan_list.append(place)
    # �������������
    ps.volume = ps.volume + block.volume
    # ѹ���µ�ʣ��ռ�
    cuboid1, cuboid2, cuboid3 = gen_residual_space(space, block)
    ps.space_stack.push(cuboid1, cuboid2, cuboid3)
    # ������ʱ���ɵķ���
    return place


# ���Ƴ��㷨
def remove_block(ps: PackingState, block: Block, place: Place, space: Space):
    # ��ԭ����������Ŀ
    ps.avail_list = (np.array(ps.avail_list) + np.array(block.require_list)).tolist()
    # ��ԭ�����ƻ�
    ps.plan_list.remove(place)
    # ��ԭ���������
    ps.volume = ps.volume - block.volume
    # �Ƴ��ڴ�֮ǰ���г����¿ռ�
    for _ in range(3):
        ps.space_stack.pop()
    # ��ԭ֮ǰ�Ŀռ�
    ps.space_stack.push(space)


# ��ȫ���÷���
def complete(ps: PackingState, block_table):
    # ���Ե�ǰ�ķ���״̬�����޸�
    tmp = copy.deepcopy(ps)
    while tmp.space_stack.not_empty():
        # ջ���ռ�
        space = tmp.space_stack.top()
        # ���ÿ��б�
        block_list = gen_block_list(space, ps.avail_list, block_table)
        if len(block_list) > 0:
            # ���ÿ�
            place_block(tmp, block_list[0])
        else:
            # �ռ�ת��
            transfer_space(space, tmp.space_stack)
    # ��ȫ���ʹ�����
    ps.volume_complete = tmp.volume


# ��������Ƶ�������������㷨
def depth_first_search(ps: PackingState, depth, branch, block_table):
    global tmp_best_ps
    if depth != 0:
        space = ps.space_stack.top()
        block_list = gen_block_list(space, ps.avail_list, block_table)
        if len(block_list) > 0:
            # �������з�֧
            for i in range(min(branch, len(block_list))):
                # ���ÿ�
                place = place_block(ps, block_list[i])
                # ������һ����
                depth_first_search(ps, depth - 1, branch, block_table)
                # �Ƴ��ղ���ӵĿ�
                remove_block(ps, block_list[i], place, space)
        else:
            # ת�ƿռ�
            old_target = transfer_space(space, ps.space_stack)
            if old_target:
                # ������һ����
                depth_first_search(ps, depth, branch, block_table)
                # ��ԭת�ƿռ�
                transfer_space_back(space, ps.space_stack, old_target)
    else:
        # ��ȫ�÷���
        complete(ps, block_table)
        # �������Ž�
        if ps.volume_complete > tmp_best_ps.volume_complete:
            tmp_best_ps = copy.deepcopy(ps)


# ����ĳ����
def estimate(ps: PackingState, block_table, search_params):
    # �յķ��÷���
    global tmp_best_ps
    # tmp_best_ps = PackingState()
    tmp_best_ps = PackingState([], Stack(), [])
    # ��ʼ�����������
    depth_first_search(ps, MAX_DEPTH, MAX_BRANCH, block_table)
    return tmp_best_ps.volume_complete


# ������һ�����п�
def find_next_block(ps: PackingState, block_list, block_table, search_params):
    # # Ҳ���Բ���̰���㷨��ֱ�ӷ������������Ŀ�
    return block_list[0]
    # ������Ӧ��
    best_fitness = 0
    # ��ʼ�����ſ�Ϊ��һ���飨���������Ŀ飩
    best_block = block_list[0]
    # �������п��п�
    for block in block_list:
        # ջ���ռ�
        space = ps.space_stack.top()
        # ���ÿ�
        place = place_block(ps, block)
        # ����ֵ
        fitness = estimate(ps, block_table, search_params)
        # �Ƴ��ղ���ӵĿ�
        remove_block(ps, block, place, space)
        # �������Ž�
        if fitness > best_fitness:
            best_fitness = fitness
            best_block = block

    return best_block


# �ݹ鹹���������꣬���ڻ�ͼ
def build_box_position(block, init_pos, box_list):
    # �����򵥿�ʱ�����������
    if len(block.children) <= 0 and block.times == 0:
        # ������������
        box_idx = (np.array(block.require_list) > 0).tolist().index(True)
        if box_idx > -1:
            # ��������
            box = box_list[box_idx]
            # ������������
            nx = block.lx / box.lx
            ny = block.ly / box.ly
            nz = block.lz / box.lz
            x_list = (np.arange(0, nx) * box.lx).tolist()
            y_list = (np.arange(0, ny) * box.ly).tolist()
            z_list = (np.arange(0, nz) * box.lz).tolist()
            # ����ľ�������
            dimensions = (np.array([x for x in product(x_list, y_list, z_list)]) + np.array([init_pos[0], init_pos[1], init_pos[2]])).tolist()
            return sorted([d + [box.lx, box.ly, box.lz] for d in dimensions], key=lambda x: (x[0], x[1], x[2]))
        return []

    pos = []
    for child in block.children:
        pos += build_box_position(child, (init_pos[0], init_pos[1], init_pos[2]), box_list)
        # �����ӿ�ĸ��Ϸ���ȷ����һ���ӿ������½�����
        if block.direction == "x":
            init_pos = (init_pos[0] + child.lx, init_pos[1], init_pos[2])
        elif block.direction == "y":
            init_pos = (init_pos[0], init_pos[1] + child.ly, init_pos[2])
        elif block.direction == "z":
            init_pos = (init_pos[0], init_pos[1], init_pos[2] + child.lz)
    return pos


# ����������߿�
def plot_linear_cube(ax, x, y, z, dx, dy, dz, color='red', linestyle=None):
    xx = [x, x, x+dx, x+dx, x]
    yy = [y, y+dy, y+dy, y, y]
    kwargs = {"alpha": 1, "color": color, "linewidth": 2.5, "zorder": 2}
    if linestyle:
        kwargs["linestyle"] = linestyle
    ax.plot3D(xx, yy, [z]*5, **kwargs)
    ax.plot3D(xx, yy, [z+dz]*5, **kwargs)
    ax.plot3D([x, x], [y, y], [z, z+dz], **kwargs)
    ax.plot3D([x, x], [y+dy, y+dy], [z, z+dz], **kwargs)
    ax.plot3D([x+dx, x+dx], [y+dy, y+dy], [z, z+dz], **kwargs)
    ax.plot3D([x+dx, x+dx], [y, y], [z, z+dz], **kwargs)


# ������
def cuboid_data2(o, size=(1, 1, 1)):
    X = [[[0, 1, 0], [0, 0, 0], [1, 0, 0], [1, 1, 0]],
         [[0, 0, 0], [0, 0, 1], [1, 0, 1], [1, 0, 0]],
         [[1, 0, 1], [1, 0, 0], [1, 1, 0], [1, 1, 1]],
         [[0, 0, 1], [0, 0, 0], [0, 1, 0], [0, 1, 1]],
         [[0, 1, 0], [0, 1, 1], [1, 1, 1], [1, 1, 0]],
         [[0, 1, 1], [0, 0, 1], [1, 0, 1], [1, 1, 1]]]
    X = np.array(X).astype(float)
    for i in range(3):
        X[:, :, i] *= size[i]
    X += np.array(o)
    return X


# ����������
def plotCubeAt2(positions, sizes=None, colors=None, **kwargs):
    if not isinstance(colors, (list, np.ndarray)):
        colors = ["C0"] * len(positions)
    if not isinstance(sizes, (list, np.ndarray)):
        sizes = [(1, 1, 1)] * len(positions)
    g = []
    for p, s, c in zip(positions, sizes, colors):
        g.append(cuboid_data2(p, size=s))
    return Poly3DCollection(np.concatenate(g), facecolors=np.repeat(colors, 6), **kwargs)


# �����������
def draw_packing_result(problem: Problem, ps: PackingState):
    # ���ƽ��
    fig = plt.figure()
    ax1 = mplot3d.Axes3D(fig, auto_add_to_figure=False)
    fig.add_axes(ax1)
    # ��������
    plot_linear_cube(ax1, 0, 0, 0, problem.container.lx, problem.container.ly, problem.container.lz)
    for p in ps.plan_list:
        # ����λ�ü��ߴ�
        box_pos = build_box_position(p.block, (p.space.x, p.space.y, p.space.z), problem.box_list)
        positions = []
        sizes = []
        # ������ɫ
        colors = ["yellow"] * len(box_pos)
        for bp in sorted(box_pos, key=lambda x: (x[0], x[1], x[2])):
            positions.append((bp[0], bp[1], bp[2]))
            sizes.append((bp[3], bp[4], bp[5]))
        pc = plotCubeAt2(positions, sizes, colors=colors, edgecolor="k")
        ax1.add_collection3d(pc)
    plt.title('PackingResult')
    plt.show()
    # plt.savefig('3d_multilayer_search.png', dpi=800)


# ��������ʽ�㷨
def basic_heuristic(is_complex, search_params, problem: Problem):
    st = time.time()
    if is_complex:
        # ���ɸ��Ͽ�
        block_table = gen_complex_block(problem.container, problem.box_list, problem.num_list)
    else:
        # ���ɼ򵥿�
        block_table = gen_simple_block(problem.container, problem.box_list, problem.num_list)
    # ��ʼ������״̬
    ps = PackingState(avail_list=problem.num_list)
    # ��ʼʱ��ʣ��ռ��ջ��ֻ����������
    ps.space_stack.push(problem.container)
    # ����ʣ��ռ��ת������ֹͣ
    while ps.space_stack.size() > 0:
        space = ps.space_stack.top()
        block_list = gen_block_list(space, ps.avail_list, block_table)
        if block_list:
            # ������һ���������ſ�
            block = find_next_block(ps, block_list, block_table, search_params)
            # ��������ʣ��ռ�
            ps.space_stack.pop()
            # ���¿�����Ʒ����
            ps.avail_list = (np.array(ps.avail_list) - np.array(block.require_list)).tolist()
            # ���������ƻ�
            ps.plan_list.append(Place(space, block))
            # �������������
            ps.volume = ps.volume + block.volume
            # ѹ���²��е�ʣ��ռ�
            cuboid1, cuboid2, cuboid3 = gen_residual_space(space, block)
            ps.space_stack.push(cuboid1, cuboid2, cuboid3)
        else:
            # ת��ʣ��ռ�
            transfer_space(space, ps.space_stack)

    # ��ӡʣ���������ʹ�����������
    et = time.time()
    cost_time = et - st
    all_volume = problem.container.lx * problem.container.ly * problem.container.lz
    #print("----------------E1----------------")
    print("--ѡȡװ��Ļ��",end = "")
    for i in range(len(ps.avail_list)):
        print("��{}������װ��{}����".format(i+1,problem.num_list[i] - ps.avail_list[i]),end = "")
    print("\n--����ʱ�䣺{:.4f}s".format(cost_time))
    print("--װ���ʣ�{:.4f}%".format(ps.volume / all_volume * 100))
    print("\n")

    print("--װ���������꣨���հڷ�˳�򣩣�")
    index = 0
    for i,p in zip(range(len(ps.plan_list)),ps.plan_list):
        box_pos = build_box_position(p.block, (p.space.x, p.space.y, p.space.z), problem.box_list)
        for item in sorted(box_pos, key=lambda x: (x[0], x[1], x[2])):
            index = index + 1
            print("-��{:^2}�����ӵ�װ�����꣺[{:^3},{:^3},{:^3}]  ".format(index,int(item[0]),int(item[1]),int(item[2])),end = "")
            if index % 3 == 0:print("")


    # �����������ͼ
    draw_packing_result(problem, ps)


# ���㷨
def main():
    # ����
    container = Space(0, 0, 0, 587, 233, 220)
    box_list = [Box(113, 92, 33, 0), Box(52, 37, 28, 1), Box(57, 33, 29, 2), Box(99, 37, 30, 3), Box(92, 64, 33, 4), Box(119, 59, 39, 5), Box(54, 52, 49, 6), Box(75, 45, 35, 7)]
    num_list = [23, 22, 26 ,17, 23, 26, 18, 30]
    '''
    all_box_list = [[Box(108, 76, 30, 0), Box(110, 43, 25, 1), Box(92, 81, 55, 2)],
                    [Box(91, 54, 45, 0), Box(105, 77, 72, 1), Box(79, 78, 48, 2)],
                    [Box(91, 54, 45, 0), Box(105, 77, 72, 1), Box(79, 78, 48, 2)],
                    [Box(60, 40, 32, 0), Box(98, 75, 55, 1), Box(60, 59, 39, 2)],
                    [Box(78, 37, 27, 0), Box(89, 70, 25, 1), Box(90, 84, 41, 2)],

                    [Box(108, 76, 30, 0), Box(110, 43, 25, 1), Box(92, 81, 55, 2), Box(81, 33, 28, 3), Box(120, 99, 73, 4)],
                    [Box(49, 25, 21, 0), Box(60, 51, 41, 1), Box(103, 76, 64, 2), Box(95, 70, 62, 3), Box(111, 49, 26, 4)],
                    [Box(88, 54, 39, 0), Box(94, 54, 36, 1), Box(87, 77, 43, 2), Box(100, 80, 72, 3), Box(83, 40, 36, 4)],
                    [Box(90, 70, 63, 0), Box(84, 78, 28, 1), Box(94, 85, 39, 2), Box(80, 76, 54, 3), Box(69, 50, 45, 4)],
                    [Box(74, 63, 61, 0), Box(71, 60, 25, 1), Box(106, 80, 59, 2), Box(109, 76, 42, 3), Box(118, 56, 22, 4)],

                    [Box(108, 76, 30, 0), Box(110, 43, 25, 1), Box(92, 81, 55, 2), Box(81, 33, 28, 3), Box(120, 99, 73, 4), Box(111, 70, 48, 5), Box(98, 72, 46, 6), Box(95, 66, 31, 7)],
                    [Box(97, 81, 27, 0), Box(102, 78, 39, 1), Box(113, 46, 36, 2), Box(66, 50, 42, 3), Box(101, 30, 26, 4), Box(100, 56, 35, 5), Box(91, 50, 40, 6), Box(106, 61, 56, 7)],
                    [Box(88, 54, 39, 0), Box(94, 54, 36, 1), Box(87, 77, 43, 2), Box(100, 80, 72, 3), Box(83, 40, 36, 4), Box(91, 54, 22, 5), Box(109, 58, 54, 6), Box(94, 55, 30, 7)],
                    [Box(49, 25, 21, 0), Box(60, 51, 41, 1), Box(103, 76, 64, 2), Box(95, 70, 62, 3), Box(111, 49, 26, 4), Box(85, 84, 72, 5), Box(48, 36, 31, 6), Box(86, 76, 38, 7)],
                    [Box(113, 92, 33, 0), Box(52, 37, 28, 1), Box(57, 33, 29, 2), Box(99, 37, 30, 3), Box(92, 64, 33, 4), Box(119, 59, 39, 5), Box(54, 52, 49, 6), Box(75, 45, 35, 7)], 

                    [Box(49, 25, 21, 0), Box(60, 51, 41, 1), Box(103, 76, 64, 2), Box(95, 70, 62, 3), Box(111, 49, 26, 4), Box(85, 84, 72, 5), Box(48, 36, 31, 6), Box(86, 76, 38, 7), Box(71, 48, 47, 8), Box(90, 43, 33, 9)],
                    [Box(97, 81, 27, 0), Box(102, 78, 39, 1), Box(113, 46, 36, 2), Box(66, 50, 42, 3), Box(101, 30, 26, 4), Box(100, 56, 35, 5), Box(91, 50, 40, 6), Box(106, 61, 56, 7), Box(103, 63, 58, 8), Box(75, 57, 41, 9)],
                    [Box(86, 84, 45, 0), Box(81, 45, 34, 1), Box(70, 54, 37, 2), Box(71, 61, 52, 3), Box(78, 73, 40, 4), Box(69, 63, 46, 5), Box(72, 67, 56, 6), Box(75, 75, 36, 7), Box(94, 88, 50, 8), Box(65, 51, 50, 9)],
                    [Box(113, 92, 33, 0), Box(52, 37, 28, 1), Box(57, 33, 29, 2), Box(99, 37, 30, 3), Box(92, 64, 33, 4), Box(119, 59, 39, 5), Box(54, 52, 49, 6), Box(75, 45, 35, 7), Box(79, 68, 44, 8), Box(116, 49, 47, 9)],
                    [Box(118, 79, 51, 0), Box(86, 32, 31, 1), Box(64, 58, 52, 2), Box(42, 42, 32, 3), Box(64, 55, 43, 4), Box(84, 70, 35, 5), Box(76, 57, 36, 6), Box(95, 60, 55, 7), Box(80, 66, 52, 8), Box(109, 73, 23, 9)],

                    [Box(98, 73, 44, 0), Box(60, 60, 38, 1), Box(105, 73, 60, 2), Box(90, 77, 52, 3), Box(66, 58, 24, 4), Box(106, 76, 55, 5), Box(55, 44, 36, 6), Box(82, 58, 23, 7), Box(74, 61, 58, 8), Box(81, 39, 24, 9), Box(71, 65, 39, 10), Box(105, 97, 47, 11), Box(114, 97, 69, 12), Box(103, 78, 55, 13), Box(93, 66, 55, 14)],
                    [Box(108, 76, 30, 0), Box(110, 43, 25, 1), Box(92, 81, 55, 2), Box(81, 33, 28, 3), Box(120, 99, 73, 4), Box(111, 70, 48, 5), Box(98, 72, 46, 6), Box(95, 66, 31, 7), Box(85, 84, 30, 8), Box(71, 32, 25, 9), Box(36, 34, 25, 10), Box(97, 67, 62, 11), Box(33, 25, 23, 12), Box(95, 27, 26, 13), Box(94, 81, 44, 14)],
                    [Box(49, 25, 21, 0), Box(60, 51, 41, 1), Box(103, 76, 64, 2), Box(95, 70, 62, 3), Box(111, 49, 26, 4), Box(74, 42, 40, 5), Box(85, 84, 72, 6), Box(48, 36, 31, 7), Box(86, 76, 38, 8), Box(71, 48, 47, 9), Box(90, 43, 33, 10), Box(98, 52, 44, 11), Box(73, 37, 23, 12), Box(61, 48, 39, 13), Box(75, 75, 63, 14)],
                    [Box(97, 81, 27, 0), Box(102, 78, 39, 1), Box(113, 46, 36, 2), Box(66, 50, 42, 3), Box(101, 30, 26, 4), Box(100, 56, 35, 5), Box(91, 50, 40, 6), Box(106, 61, 56, 7), Box(103, 63, 58, 8), Box(75, 57, 41, 9), Box(71, 68, 64, 10), Box(85, 67, 39, 11), Box(97, 63, 56, 12), Box(61, 48, 30, 13), Box(80, 54, 35, 14)],
                    [Box(113, 92, 33, 0), Box(52, 37, 28, 1), Box(57, 33, 29, 2), Box(99, 37, 30, 3), Box(92, 64, 33, 4), Box(119, 59, 39, 5), Box(54, 52, 49, 6), Box(75, 45, 35, 7), Box(79, 68, 44, 8), Box(116, 49, 47, 9), Box(83, 44, 23, 10), Box(98, 96, 56, 11), Box(78, 72, 57, 12), Box(98, 88, 47, 13), Box(41, 33, 31, 14)]]
    '''
    '''
    all_num_list = [[40, 33, 39],
                    [32, 24, 30],
                    [32, 24, 30],
                    [64, 40, 64],
                    [63, 52, 55],

                    [24, 7, 22, 13, 15],
                    [22, 22, 28, 25, 17],
                    [25, 27, 21, 20, 24],
                    [16, 28, 20, 23, 31],
                    [22, 12, 25, 24, 11],

                    [24, 9, 8, 11, 11, 10, 12, 9],
                    [10, 20, 18, 21, 16, 17, 22, 19],
                    [16, 14, 20, 16, 6, 15, 17, 9],
                    [16, 8, 16, 18, 18, 16, 17, 6],
                    [23, 22, 26 ,17, 23, 26, 18, 30],

                    [13, 9, 11, 14, 13, 16, 12, 11, 16, 8],
                    [8, 16, 12, 12, 18, 13, 14, 17, 12, 13],
                    [18, 19, 13, 16, 10, 13, 10, 8, 12, 13],
                    [15, 17, 17, 19, 13, 19, 13, 21, 13, 22],
                    [16, 8, 14, 14, 16, 10, 14, 14, 14, 18],

                    [6, 7, 10, 3, 5, 10, 12, 7, 6, 8, 11, 4, 5, 6, 6],
                    [12, 12, 6, 9, 5, 12, 9, 10, 8, 3, 10, 7, 7, 10, 9],
                    [13, 9, 8, 6, 10, 4, 10, 10, 12, 14, 9, 9, 10, 14, 11],
                    [6, 6, 15, 8, 6, 7, 12, 10, 8, 11, 6, 14, 9, 11, 9],
                    [8, 12, 5, 12, 9, 12, 8, 6, 12, 9, 11, 10, 8, 9, 13]]
    '''
    
    '''
    for i in range(len(all_box_list)):
        box_list = all_box_list[i]
        num_list = all_num_list[i]
        problem = Problem(container, box_list, num_list)
        search_params = dict()
        print("----------------E{}-{}----------------".format(int(i / 5 + 1),i % 5 + 1))
        basic_heuristic(True, search_params, problem)
    '''


    # ����
    problem = Problem(container, box_list, num_list)
    search_params = dict()
    # �������
    basic_heuristic(True, search_params, problem



if __name__ == "__main__":
    main()


