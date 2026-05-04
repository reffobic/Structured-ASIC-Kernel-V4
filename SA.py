import math 
import random
from placer import Grid
from collections import defaultdict

num_cells = Grid.num_cells
num_nets = Grid.num_nets
initial_cost = hpwl(cells) #implemented by Haya 
T = 500*initial_cost
T_fin = (5e5 * initial_cost) / num_nets
num_moves = 20*num_cells

def SA_loop(CR):
    cells = Grid.movable_cells()
    cells_by_type = defaultdict(list)
    for cell in cells:
        cells_by_type[cell.cell_type].append(cell)

    current_cost = initial_cost
    accepted_moves = 0
    rejected_moves = 0
    
    while T > T_fin:

        for i in range(num_moves):
            cell1 = random.choice(cells)
            same_type_cells = cells_by_type[cell1.cell_type]

            if len(same_type_cells) < 2:
                continue

            cell2 = random.choice(same_type_cells)
            delta_cost = swap_cells(cell1, cell2) #implemented by Haya

            if delta_cost < 0:
                current_cost += delta_cost
                accepted_moves += 1

            else:
                p = math.exp(-delta_cost / T)

                if random.random() < p:
                    current_cost += delta_cost
                    accepted_moves += 1

                else:
                    swap_cells(cell2, cell1) #revert the swap
                    rejected_moves += 1
                    
        T*= CR
    
    return current_cost, accepted_moves, rejected_moves
                
