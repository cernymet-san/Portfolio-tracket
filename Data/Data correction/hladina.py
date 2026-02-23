import numpy as np

def generate_fluctuating_vector(y, x, fluctuation_range, decimals):
    """
    Generate a list of x numbers randomly fluctuating around a value y.

    Parameters:
    y (float): The central value around which the numbers fluctuate.
    x (int): The number of elements in the list.
    fluctuation_range (float): The maximum deviation from the central value y.
    decimals (int): The number of decimal places for each element.

    Returns:
    list of str: The formatted list with each element as a string with specified decimal places.
    """
    # Generate random fluctuations around y
    fluctuations = np.random.uniform(-fluctuation_range, fluctuation_range, x)
    fluctuating_vector = y + fluctuations
    formatted_vector = [f"{element:.{decimals}f}" for element in fluctuating_vector]
    return formatted_vector

# Example usage
y = -1021
x = 25
#22*63+50
fluctuation_range = 1.8
decimals = 12  # Specify the number of decimal places

fluctuating_vector = generate_fluctuating_vector(y, x, fluctuation_range, decimals)

# Print each formatted element individually
for element in fluctuating_vector:
    print(element)