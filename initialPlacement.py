from Placer import netlist_editor, parse_netlist

# Load the grid from the netlist file - still need to allow user to specify the file name, currently using placeholder
grid = parse_netlist("design_1_small.txt") 


# Legalization helper functions ---------------------------------------------------------------------------------------------
def find_nearest_legal_pos(component, grid):
    '''
    This function finds the nearest legal position for a given component on the grid.
    '''

    x = component.x
    y = component.y
    nearest_position = None
    min_distance = float('inf') # Set initial minimum distance to infinity initially 

    search_space = grid.iter_core_sites()  # Get all core sites to search through

    for site in search_space:
        if site.site_type == component.cell_type and site.is_empty(): # If the current site is a type match AND not already occupied
            distance = abs(site.x - x) + abs(site.y - y)  # Manhattan distance (better than eucliden distance for grid-based movement)
            if distance < min_distance:
                min_distance = distance
                nearest_position = (site.x, site.y)

    return nearest_position 

def move_comp(component, new_position, grid):
    '''
    This function moves the component to a new position on the grid.
    '''    

    # Update the grid's sites vacancy
    grid.site_at(new_position[0], new_position[1]).cell_id = component.component_id  # Assign the component to the new site
    grid.site_at(component.x, component.y).cell_id = None  # Mark the old site as vacant

    # Update the component object's position
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
    original_pos1 = (component1.x, component1.y)
    original_pos2 = (component2.x, component2.y)

    # SA already validates cells before calling swap 
    # if(component1.cell_type != component2.cell_type): # Types must match to swap
    #     raise netlist_editor("Components must be of the same type to swap")
    # else:
    
    # Swap the positions of the two components on the grid
    grid.site_at(component1.x, component1.y).cell_id = component2.component_id
    grid.site_at(component2.x, component2.y).cell_id = component1.component_id

    # Update the component objects' positions
    component1.x, component1.y, component2.x, component2.y = original_pos2[0], original_pos2[1], original_pos1[0], original_pos1[1]


def hpwl(net):
    '''
    This function calculates the Half Perimeter Wire Length (HPWL) of a given net. 
    '''

    # Fetch the components connected to the net using their IDs
    comp_ids = net.component_ids
    connected_components = [grid.components[comp_id] for comp_id in comp_ids]

    # Determine the net's bounding box by finding the maximum and minimum x and y coordinates of the connected components
    max_x = max(comp.x for comp in connected_components)
    min_x = min(comp.x for comp in connected_components)
    max_y = max(comp.y for comp in connected_components)
    min_y = min(comp.y for comp in connected_components)

    # Calculate the half-perimeter wire length
    hpwl = (max_x - min_x) + (max_y - min_y)

    return hpwl


