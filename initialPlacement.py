from Placer import netlist_error, parse_netlist

# Legalization helper functions ---------------------------------------------------------------------------------------------
def find_nearest_legal_pos(component, grid):
    '''
    This function finds the nearest legal position for a given component on the grid.
    '''

    x = component.x if component.x is not None else component.placement_x
    y = component.y if component.y is not None else component.placement_y
    if x is None or y is None:
        return None
    nearest_position = None
    min_distance = float('inf') # Set initial minimum distance to infinity initially 

    search_space = grid.iter_core_sites()  # Get all core sites to search through

    for site in search_space:
        if site.site_type == component.cell_type and site.is_empty: # If the current site is a type match AND not already occupied
            distance = abs(site.x - x) + abs(site.y - y)  # Manhattan distance (better than eucliden distance for grid-based movement)
            if distance < min_distance:
                min_distance = distance
                nearest_position = (site.x, site.y)

    return nearest_position 

def move_comp(component, new_position, grid):
    '''
    This function moves the component to a new position on the grid.
    '''    

    if new_position is None:
        return
    # Move using placer API, then mirror x/y for existing naming compatibility.
    grid.attach_cell_to_at(component.component_id, new_position[0], new_position[1])
    component.x, component.y = new_position

# ---------------------------------------------------------------------------------------------------------------------------- 


def legalize(grid):
    '''
    This function implements Tetris-Placement Legalization.
    Legalization criteria:
    1)Not in the perimeter (already guaranteed by the input)
    2)The tile type is complementary to the component type 
    3)Components do not overlap i.e. a component cannot be placed on an occupied site 
    
    Placement:
    Minimum displacement i.e. nearest legal position 
    '''
    # Fetch movable components of the passed grid
    movable_comps = grid.movable_cells()

    for comp in movable_comps:
        if comp.placement_x is None or comp.placement_y is None:
            # If the cell has no prior coordinates, "nearest" is undefined; choose any legal empty site.
            new_position = None
            for site in grid.iter_core_sites():
                if site.site_type == comp.cell_type and site.is_empty:
                    new_position = (site.x, site.y)
                    break
            if new_position is None:
                raise netlist_error(f"No legal empty site found for cell {comp.component_id} type {comp.cell_type}.")
            move_comp(comp, new_position, grid)
            continue

        comp.x, comp.y = comp.placement_x, comp.placement_y
        # Check if the component is already in a legal position
        if grid.site_at(comp.x, comp.y).site_type == comp.cell_type:
            continue  
        else:
            # Find the nearest legal position
            new_position = find_nearest_legal_pos(comp, grid)
            # Move the component to the new position
            move_comp(comp, new_position, grid)

    
def swap(component1, component2, grid):
    '''
    This function swaps the positions of two components on the grid, meant to be used by SA later.
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

def total_hpwl(grid):
    return sum(hpwl(grid, n) for n in grid.nets)


