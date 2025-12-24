import numpy as np
from PIL import Image
import random

class Point:
    def __init__(self, coords):
        self.coords = coords

    def __repr__(self):
        return f"Point({self.coords})"

class Cluster:
    def __init__(self, points):
        if len(points) == 0:
            raise Exception("Cluster cannot be empty")
        self.points = points
        self.center = self.calculate_center()

    def calculate_center(self):
        coords = [p.coords for p in self.points]
        return Point([sum(coord) / len(coord) for coord in zip(*coords)])

    def update_center(self):
        old_center = self.center
        self.center = self.calculate_center()
        return old_center.coords != self.center.coords

    def __repr__(self):
        return f"Cluster({self.center}, {len(self.points)} points)"

def get_points(img):
    """Extract color points from image"""
    points = []
    pixels = img.load()
    width, height = img.size

    # Sample pixels to avoid too many points
    step = max(1, min(width, height) // 100)

    for y in range(0, height, step):
        for x in range(0, width, step):
            try:
                r, g, b = pixels[x, y][:3]  # Ignore alpha if present
                points.append(Point([r, g, b]))
            except:
                continue

    return points

def kmeans(points, k, max_iterations=10):
    """Simple k-means clustering implementation"""
    if len(points) < k:
        # If we have fewer points than clusters, return all points as separate clusters
        clusters = []
        for i, point in enumerate(points):
            clusters.append(Cluster([point]))
        # Pad with empty clusters if needed
        while len(clusters) < k:
            # Create a random point
            random_point = Point([random.randint(0, 255) for _ in range(3)])
            clusters.append(Cluster([random_point]))
        return clusters

    # Initialize centroids randomly
    centroids = []
    for _ in range(k):
        random_point = random.choice(points)
        centroids.append(Point(random_point.coords.copy()))

    for _ in range(max_iterations):
        # Assign points to closest centroid
        clusters = [[] for _ in range(k)]
        for point in points:
            distances = [np.linalg.norm(np.array(point.coords) - np.array(centroid.coords)) for centroid in centroids]
            closest_centroid_idx = np.argmin(distances)
            clusters[closest_centroid_idx].append(point)

        # Remove empty clusters and replace with random points
        for i in range(len(clusters)):
            if len(clusters[i]) == 0:
                clusters[i] = [random.choice(points)]

        # Update centroids
        new_centroids = []
        for cluster_points in clusters:
            if cluster_points:
                coords = [p.coords for p in cluster_points]
                new_center = [sum(coord) / len(coord) for coord in zip(*coords)]
                new_centroids.append(Point(new_center))
            else:
                new_centroids.append(random.choice(points))

        centroids = new_centroids

    # Create final clusters
    final_clusters = []
    for i, cluster_points in enumerate(clusters):
        if cluster_points:
            final_clusters.append(Cluster(cluster_points))

    return final_clusters

