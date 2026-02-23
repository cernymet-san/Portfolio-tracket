import numpy as np

def generate_trend_random_vector(p0, p1, x, decimals, randomness_factor=1):
    """
    Generate a random vector with x elements following a trend from pmin to pmax
    with each element having a specified number of decimal places.

    Parameters:
    pmin (float): The minimum value of the range.
    pmax (float): The maximum value of the range.
    x (int): The number of elements in the vector.
    decimals (int): The number of decimal places for each element.
    randomness_factor (float): Factor to control the amount of randomness.

    Returns:
    list of str: The formatted vector with each element as a string with specified decimal places.
    """
    linear_vector = np.linspace(p0, p1, x)
    perturbation = np.random.uniform(-randomness_factor, randomness_factor, x)
    random_trend_vector = linear_vector + perturbation
    formatted_vector = [f"{element:.{decimals}f}" for element in random_trend_vector]
    return formatted_vector

# Example usage
p0 = 300
p1 = 0
x = 25
decimals = 12  # Specify the number of decimal places

random_trend_vector = generate_trend_random_vector(p0, p1, x, decimals)

# Print each formatted element individually
for element in random_trend_vector:
    print(element)