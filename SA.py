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
    
    if(component1.cell_type != component2.cell_type) and (component1.cell_type is not None or component2.cell_type is not None): # Types must match to swap
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

def initial_total_hpwl(grid):
    '''
    This function calculates the total HPWL of the grid by summing the HPWL of all nets, meant to be used before SA when we don't have a previous grid to compare to.
    '''
    total_hpwl = 0
    for net in grid.nets:
        total_hpwl += hpwl(grid, net)

    return total_hpwl

def build_cell_to_nets(g):
    cell_to_nets = defaultdict(set)
    for net in g.nets:
        for comp_id in net.component_ids:
            cell_to_nets[comp_id].add(net)
    return cell_to_nets

def partial_hpwl_fast(cell1, cell2, g, cell_to_nets):
    touched = cell_to_nets[cell1.component_id] | cell_to_nets[cell2.component_id]
    return sum(hpwl(g, net) for net in touched)

# def hpwl_fast(n, coords):
#     '''
#     Faster HPWL using precomputed coordinates dict instead of reading from grid objects.
#     '''
#     xs = [coords[cid][0] for cid in n.component_ids]
#     ys = [coords[cid][1] for cid in n.component_ids]
#     return (max(xs) - min(xs)) + (max(ys) - min(ys))

# NEW third attempted optimization: manual min/max without lists. Still keeping the coords dict for O(1) lookups but avoiding the overhead of lists and built-in max/min functions.
def hpwl_fast(n, coords):
    '''
    Faster HPWL using precomputed coordinates dict instead of reading from grid objects.
    '''
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for cid in n.component_ids:
        x, y = coords[cid]
        if x < min_x: min_x = x
        if x > max_x: max_x = x
        if y < min_y: min_y = y
        if y > max_y: max_y = y
    return (max_x - min_x) + (max_y - min_y)
# ---------------------------------------------------------------------------------------------------------------------------------


def SA_loop(CR, g):
    num_cells   = g.num_cells
    num_nets    = g.num_nets
    cells       = g.movable_cells()
    num_moves   = 20 * num_cells

    cell_to_nets = build_cell_to_nets(g)

    cells_by_type = defaultdict(list)
    for cell in cells:
        cells_by_type[cell.cell_type].append(cell)

    # coords = {}
    # for comp in g.components.values():
    #     coords[comp.component_id] = (
    #         comp.x if comp.is_pin else comp.placement_x,
    #         comp.y if comp.is_pin else comp.placement_y,
    #     )

    # net_hpwl_cache = {n.net_id: hpwl_fast(n, coords) for n in g.nets}

    #  NEW first attempted optimization: list instead of dict for the same lookup efficiency but without hashing overhead
    max_id = max(g.components.keys())  

    coords = [None] * (max_id + 1)     

    for comp in g.components.values():
        coords[comp.component_id] = (
            comp.x if comp.is_pin else comp.placement_x, # Keep pins check since it's needed for HPWL calculation 
            comp.y if comp.is_pin else comp.placement_y,
        )
    
    net_hpwl_cache = [0.0] * num_nets  
    for n in g.nets:
        net_hpwl_cache[n.net_id] = hpwl_fast(n, coords)
    # -------------------------------------------------------------------------------------------------------------- 

    current_cost = sum(net_hpwl_cache)
    initial_cost   = current_cost

    T     = 500 * initial_cost
    T_fin = (5e-5 * initial_cost) / num_nets

    accepted_moves = 0
    rejected_moves = 0

    while T > T_fin:
        # NEW second attempted optimization: instead of picking a random cell then finding its type group AND precompute type_keys outside the loop since it never changes 
        valid_type_keys = [k for k, v in cells_by_type.items() if len(v) >= 2]

        for _ in range(num_moves):
            # NEW second attempted optimization continued
            type_list = cells_by_type[random.choice(valid_type_keys)]
            # type_list = cells_by_type[random.choice(cells).cell_type]

            # This is already being checked now outside the loop with valid_type_keys  
            # if len(type_list) < 2:
            #     continue

            idx1 = random.randrange(len(type_list))
            idx2 = random.randrange(len(type_list) - 1)
            if idx2 >= idx1:
                idx2 += 1
            cell1, cell2 = type_list[idx1], type_list[idx2]

            # delta cost using caches
            touched      = cell_to_nets[cell1.component_id] | cell_to_nets[cell2.component_id]
            cost_before  = sum(net_hpwl_cache[n.net_id] for n in touched)

            # tentative swap in coords only
            x1, y1 = coords[cell1.component_id]
            x2, y2 = coords[cell2.component_id]
            coords[cell1.component_id] = (x2, y2)
            coords[cell2.component_id] = (x1, y1)

            cost_after = sum(hpwl_fast(n, coords) for n in touched)
            delta_cost = cost_after - cost_before

            if delta_cost < 0 or random.random() < math.exp(-delta_cost / T):
                #accept: commit to grid and update cache
                swap(cell1, cell2, g)
                for n in touched:
                    net_hpwl_cache[n.net_id] = hpwl_fast(n, coords)
                current_cost += delta_cost
                accepted_moves += 1
            else:
                #reject: revert coords dict only (no grid touch needed)
                coords[cell1.component_id] = (x1, y1)
                coords[cell2.component_id] = (x2, y2)
                rejected_moves += 1

        T *= CR

    return initial_cost, current_cost, accepted_moves, rejected_moves
