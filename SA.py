import math 
import random
from Placer import grid
from initialPlacement import total_hpwl, swap
from collections import defaultdict



def SA_loop(CR, g):
    num_cells = g.num_cells
    num_nets = g.num_nets
    initial_cost = total_hpwl(g) #implemented by Haya 
    T = 500*initial_cost
    T_fin = (5e-5 * initial_cost) / num_nets
    num_moves = 20*num_cells
    cells = g.movable_cells()
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
            swap(cell1, cell2, g) #implemented by Haya
            new_cost = total_hpwl(g) #implemented by Haya
            delta_cost = new_cost - current_cost
            if delta_cost < 0:
                current_cost = new_cost
                accepted_moves += 1

            else:
                p = 1-math.exp(-delta_cost / T)

                if random.random() > p:
                    current_cost = new_cost
                    accepted_moves += 1

                else:
                    swap(cell1, cell2, g) #revert the swap
                    rejected_moves += 1

        T*= CR
    
    return current_cost, accepted_moves, rejected_moves
                
