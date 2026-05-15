from random import random
from Placer import netlist_error

# Placement helper functions ---------------------------------------------------------------------------------------------
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

def count_placed_cells(g):
    '''
    Helper function to count placed cells, for logging outputs. 
    '''
    return sum(1 for c in g.movable_cells() if c.placement_x is not None and c.placement_y is not None)
# ---------------------------------------------------------------------------------------------------------------------------- 


def global_placement(g):
    """
    Deterministic global placement. For each movable cell, pick a random, empty coordinate on the core area.
    Returns number of placed cells. 
    """

    placed = 0

    # Build a list of all possible (non-perimeter) empty coordinates
    empty_sites: list[tuple[int, int]] = []
    for s in g.iter_core_sites(): # Fetch all core sites to populate empty_sites 
        if s.is_empty:
            empty_sites.append((s.x, s.y))

    for cell in g.movable_cells():
        if cell.placement_x is not None and cell.placement_y is not None: # If the cell already has coordinates
            continue

        if not empty_sites:
            raise netlist_error("No empty core sites left for placement.")

        idx = random.randrange(len(empty_sites))
        x, y = empty_sites.pop(idx)
        g.attach_cell_to_at(cell.component_id, x, y)
        placed += 1

    return placed


def placement(grid):
    '''
    This function implements site placement.
    The criteria:
    1)Not in the perimeter (already guaranteed by global placement)
    2)The tile type is complementary to the component type 
    3)Components do not overlap i.e. a component cannot be placed on an occupied site 
    4)Minimum displacement i.e. nearest legal position 
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

    



