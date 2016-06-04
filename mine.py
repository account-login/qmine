import random


class Matrix:
    def __init__(self, x, y, placeholder=None):
        self._list = [placeholder] * (x * y)
        self.x = x
        self.y = y
    
    def __getitem__(self, idx):
        x, y = idx
        assert(0 <= x < self.x and 0 <= y < self.y)
        return self._list[y * self.x + x]
    
    def __setitem__(self, idx, value):
        x, y = idx
        assert(0 <= x < self.x and 0 <= y < self.y)
        self._list[y * self.x + x] = value
    
    def __iter__(self):
        return iter(self._list)
        
    def rows(self):
        for start in range(self.y):
            yield self._list[(start * self.x) : ((start + 1) * self.x)]
    
    def neighbors(self, x, y):
        assert(0 <= x < self.x and 0 <= y < self.y)
        for nx in [x - 1, x, x + 1]:
            for ny in [y - 1, y, y + 1]:
                if 0 <= nx < self.x and 0 <= ny < self.y and (nx, ny) != (x, y):
                    yield nx, ny


class MineField(Matrix):
    def __init__(self, x, y, num=0, exclude=None):
        super().__init__(x, y, placeholder=False)
        self.num = num
        if num != 0:
            if exclude is None:
                assert(num < x * y)
                self._list = [True] * num + [False] * (x * y - num)
                random.shuffle(self._list)
            else:
                assert(num <= x * y - 1)
                self._list = [True] * num + [False] * (x * y - num - 1)
                random.shuffle(self._list)
                ex, ey = exclude
                assert(0 <= ex < x and 0 <= ey < y)
                self._list.insert(ey * x + ex, False)
    
    def __setitem__(self, idx, value):
        prev = self[idx]
        if prev is True and value is False:
            self.num -= 1
        elif prev is False and value is True:
            self.num += 1
        elif prev == value:
            pass
        else:
            assert(False)
        
        super().__setitem__(idx, value)


class MineServer:
    GOOD = 'good'
    FAILED = 'failed'
    WIN = 'win'
    
    def __init__(self, x, y, num):
        self.x = x
        self.y = y
        self.num = num
        self.box_left = x * y
        self.mine_field = None
        self._clicked = Matrix(x, y, placeholder=False)
    
    def click(self, x, y):
        assert(0 <= x < self.x and 0 <= y < self.y)
        # generate mine field on first click
        if self.mine_field is None:
            self.mine_field = MineField(self.x, self.y, self.num, exclude=(x, y))
        
        if self.mine_field[x, y]:
            # BOOM
            return dict(
                status = self.FAILED,
                mine_field = self.mine_field,
            )
        else:
            # continuing
            if self._clicked[x, y]:
                # noop. click on clicked box.
                return dict(status = self.GOOD, update = dict())
            
            self._clicked[x, y] = True
            self.box_left -= 1
            
            neighbors = [ nb for nb in self.mine_field.neighbors(x, y) if not self._clicked[nb] ]
            count_mine = [ self.mine_field[nx, ny] for nx, ny in neighbors ].count(True)
            if count_mine == 0:
                # click on zero, clear all neighboring boxes.
                to_update = {(x, y): 0}
                to_explore = set(neighbors)
                ret = dict(status = self.GOOD, update = to_update)
                while to_explore:
                    new_explore = set()
                    for ex in to_explore:
#                         assert(self._clicked[ex] == False)
                        self._clicked[ex] = True
                        self.box_left -= 1
                        
                        neighbors = [ nb for nb in self.mine_field.neighbors(*ex) if not self._clicked[nb] ]
                        mines = [ self.mine_field[nb] for nb in neighbors ].count(True)
                        to_update[ex] = mines
                        if mines == 0:
                            for nb in neighbors:
                                if nb not in to_explore and nb not in new_explore:
                                    new_explore.add(nb)
                    to_explore = new_explore
            else:
                # click on a nonzero number
                ret = dict(update = {(x, y): count_mine})
            
            if self.box_left == self.num:
                ret['status'] = self.WIN
            else:
                ret['status'] = self.GOOD
            return ret


class MineClientState(Matrix):
    FLAGED = 'flaged'
    MARKED = 'marked'
    
    def __init__(self, x, y):
        super().__init__(x, y)
        
    def __repr__(self):
        ret = ''
        for line in self.rows():
            s = ''
            for n in line:
                if n is None:
                    s += '|_'
                elif n == self.FLAGED:
                    s += '|F'
                elif n == self.MARKED:
                    s += '|M'
                else:
                    s += '|%d' % n
            s += '|\n'
            ret += s
        return ret
    
    def update(self, result):
        if result['status'] in {MineServer.GOOD, MineServer.WIN}:
            for k, v in result['update'].items():
                x, y = k
                self[x, y] = v
        elif result['status'] == MineServer.FAILED:
            pass
        else:
            assert(False)

