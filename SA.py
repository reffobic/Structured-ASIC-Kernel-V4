import math 
import random
from Placer import grid, netlist_error
from collections import defaultdict

# Simulated Annealing helper functions ---------------------------------------------------------------------------------------------
def swap(component1, component2, grid):
    '''
    This function swaps the positions of two components on the grid.
    '''

    # Store the original positions of the components
    x1 = component1.x if component1.x is not None else component1.placement_x
    y1 = component1.y if component1.y is not None else component1.placement_y
    x2 = component2.x if component2.x is not None else component2.placement_x
    y2 = component2.y if component2.y is not None else component2.placement_y
    if x1 is None or y1 is None or x2 is None or y2 is None:
        raise netlist_error("Both components must have valid positions to swap")
    original_pos1 = (x1, y1)
    original_pos2 = (x2, y2)
    
    if(component1.cell_type != component2.cell_type): # Types must match to swap
        raise netlist_error("Components must be of the same type to swap")
    else:
        # Swap the positions of the two components on the grid.
        grid.detach_cell_from(component1.component_id)
        grid.detach_cell_from(component2.component_id)
        grid.attach_cell_to_at(component1.component_id, original_pos2[0], original_pos2[1])
        grid.attach_cell_to_at(component2.component_id, original_pos1[0], original_pos1[1])
        component1.x, component1.y = original_pos2[0], original_pos2[1]
        component2.x, component2.y = original_pos1[0], original_pos1[1]


def hpwl(grid, net):
    '''
    This function calculates the Half Perimeter Wire Length (HPWL) of a given net. 
    '''

    # Fetch the components connected to the net using their IDs
    comp_ids = net.component_ids
    connected_components = [grid.components[comp_id] for comp_id in comp_ids]

    # Determine the net's bounding box by finding the maximum and minimum x and y coordinates of the connected components
    xs = [comp.x if comp.x is not None else comp.placement_x for comp in connected_components]
    ys = [comp.y if comp.y is not None else comp.placement_y for comp in connected_components]
    if any(v is None for v in xs + ys):
        raise netlist_error(f"Net {net.net_id} includes unplaced component(s).")
    max_x = max(xs)
    min_x = min(xs)
    max_y = max(ys)
    min_y = min(ys)

    # Calculate the half-perimeter wire length
    hpwl = (max_x - min_x) + (max_y - min_y)

    return hpwl

def total_hpwl(old_grid, new_grid):
    '''
    Total HPWL of the grid = sum of HPWL of only the changed nets in the grid.
    '''
    changed_nets = set()
    total_hpwl = 0

    for new_cell in new_grid.movable_cells():
        for old_cell in old_grid.movable_cells():
            if new_cell.placement_x != old_cell.placement_x or new_cell.placement_y != old_cell.placement_y:
                # Add the net connected to this component to the set of changed nets
                if new_cell.net_id is not None:
                    changed_nets.add(new_cell.net_id)

    for net_id in changed_nets:
        net = new_grid.nets[net_id]
        total_hpwl += hpwl(new_grid, net)

    return total_hpwl
# -------------------------------------------------------------------------------------------------------------

def SA_loop(CR, g):
    num_cells = g.num_cells
    num_nets = g.num_nets
    initial_cost = total_hpwl(g) # implemented by Haya 
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

            # Pre-swap validation checks 
            if (not cell1.cell_type == cell2.cell_type) and (cell1.cell_type is not None or cell2.cell_type is not None):
                print("Warning: Attempting to swap two cells of different types. Skipping this move.")
                continue

            swap(cell1, cell2, g) # implemented by Haya
            new_cost = total_hpwl(g) # implemented by Haya
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
                    swap(cell1, cell2, g) # revert the swap
                    rejected_moves += 1

        T*= CR
    
    return current_cost, accepted_moves, rejected_moves
                
