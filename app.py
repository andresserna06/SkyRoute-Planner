from services.graphService import load_from_json


def main():
    # Load the air route network from the JSON file
    # Make sure to update your JSON file keys as well!
    graph = load_from_json("data/air_network.json")

    # Open the interactive graph visualization
    graph.visualize()


if __name__ == "__main__":
    main()