import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load your dataset into a pandas DataFrame
# Make sure your dataset has the columns: 'author', 'title', 'publisher', 'year', 'location'
df = pd.read_excel("book_list.xlsx")

# Combine all features into a single text column for each book
df['features'] = df.apply(lambda row: f"{row['Author']} {row['Title']} {row['Publisher']} {row['Year']} {row['Location']}", axis=1)

# Convert text features to a matrix of token counts using CountVectorizer
vectorizer = CountVectorizer()
feature_matrix = vectorizer.fit_transform(df['features'])

# Function to find the top 10 most similar books
def find_top_10_similar_books(book_index):
    # Calculate cosine similarity between the given book and all other books
    cosine_sim = cosine_similarity(feature_matrix[book_index], feature_matrix)[0]
    
    # Get the indices of the top 10 most similar books (excluding itself)
    top_10_indices = cosine_sim.argsort()[-11:-1][::-1]
    
    # Return the top 10 most similar books
    return df.iloc[top_10_indices]

# Example usage:
# Assuming you want to find the top 10 most similar books to the book at index 0 in the DataFrame
book_index = 1
top_10_similar_books = find_top_10_similar_books(book_index)
print(f"Top 10 most similar books to the book at index {book_index}:")
print(top_10_similar_books)