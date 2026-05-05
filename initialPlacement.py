from Placer import netlist_error

# Load the grid from the netlist file - still need to allow user to specify the file name, currently using placeholder
#grid = parse_netlist("design_1_small.txt") 


# Legalization helper functions ---------------------------------------------------------------------------------------------
def find_nearest_legal_pos(component, g):
    '''
    This function finds the nearest legal position for a given component on the grid.
    '''

    x = component.x if component.x is not None else component.placement_x
    y = component.y if component.y is not None else component.placement_y
    if x is None or y is None:
        return None
    
    nearest_position = None
    min_distance = float('inf') # Set initial minimum distance to infinity initially 

    search_space = g.iter_core_sites()  # Get all core sites to search through

    for site in search_space:
        if site.site_type == component.cell_type and site.is_empty(): # If the current site is a type match AND not already occupied
            distance = abs(site.x - x) + abs(site.y - y)  # Manhattan distance (better than eucliden distance for grid-based movement)
            if distance < min_distance:
                min_distance = distance
                nearest_position = (site.x, site.y)

    return nearest_position 

def move_comp(component, new_position, g):
    '''
    This function moves the component to a new position on the grid.
    '''    

    # Update the grid's sites vacancy
    if new_position is None:
            return
        # Move using placer API, then mirror x/y for existing naming compatibility.
    g.attach_cell_to_at(component.component_id, new_position[0], new_position[1])

    # Update the component object's position
    component.x, component.y = new_position

# ---------------------------------------------------------------------------------------------------------------------------- 


def legalize(g):
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
    movable_comps = g.movable_cells()

    for comp in movable_comps:
        if comp.placement_x is None or comp.placement_y is None:
            new_position = find_nearest_legal_pos(comp, g)
            move_comp(comp, new_position, g)
            continue

        comp.x, comp.y = comp.placement_x, comp.placement_y
        # Check if the component is already in a legal position
        if g.site_at(comp.x, comp.y).site_type == comp.cell_type:
            continue  
        else:
            # Find the nearest legal position
            new_position = find_nearest_legal_pos(comp, g)
            # Move the component to the new position
            move_comp(comp, new_position, g)
        # Check if the component is already in a legal position
        if g.site_at(comp.x, comp.y).site_type == comp.cell_type:
            continue  
        else:
            # Find the nearest legal position
            new_position = find_nearest_legal_pos(comp, g)
            # Move the component to the new position
            move_comp(comp, new_position, g)

    
def swap(component1, component2, g):
    '''
    This function swaps the positions of two components on the grid, meant to be used by SA later.
    '''

    # Store the original positions of the components
    original_pos1 = (component1.x, component1.y)
    original_pos2 = (component2.x, component2.y)

    # SA already validates cells before calling swap 
    # if(component1.cell_type != component2.cell_type): # Types must match to swap
    #     raise netlist_editor("Components must be of the same type to swap")
    # else:
    
    # Swap the positions of the two components on the grid
    g.site_at(component1.x, component1.y).cell_id = component2.component_id
    g.site_at(component2.x, component2.y).cell_id = component1.component_id

    # Update the component objects' positions
    component1.x, component1.y, component2.x, component2.y = original_pos2[0], original_pos2[1], original_pos1[0], original_pos1[1]


def hpwl(net):
    '''
    This function calculates the Half Perimeter Wire Length (HPWL) of a given net. 
    '''

    # Fetch the components connected to the net using their IDs
    comp_ids = net.component_ids
    connected_components = [g.components[comp_id] for comp_id in comp_ids]

    # Determine the net's bounding box by finding the maximum and minimum x and y coordinates of the connected components
    max_x = max(comp.x for comp in connected_components)
    min_x = min(comp.x for comp in connected_components)
    max_y = max(comp.y for comp in connected_components)
    min_y = min(comp.y for comp in connected_components)

    # Calculate the half-perimeter wire length
    hpwl = (max_x - min_x) + (max_y - min_y)

    return hpwl

def total_hpwl(g):
    return sum(hpwl(n) for n in g.nets)


