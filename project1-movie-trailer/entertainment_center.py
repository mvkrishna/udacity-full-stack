import fresh_tomatoes
import media

# Initializing favorite movies using Movies class from media module
minions = media.Movie("Minions",
                      "Minions are small, yellow pill-like creatures who have existed since the beginning of time",  # noqa
                      "https://upload.wikimedia.org/wikipedia/en/3/3d/Minions_poster.jpg",  # noqa
                      "https://www.youtube.com/watch?v=dVDk7PXNXB8",
                      "Pierre Coffin, Kyle Balda")

forest_gump = media.Movie("Forest Gump",
                          "Forrest Gump is a 1994 American epic romantic-comedy-drama film",  # noqa
                          "https://upload.wikimedia.org/wikipedia/en/6/67/Forrest_Gump_poster.jpg",  # noqa
                          "https://www.youtube.com/watch?v=uPIEn0M8su0",
                          "Robert Zemeckis")

finding_nemo = media.Movie("Finding nemo",
                           "Finding Nemo is a 2003 American computer-animated comedy-drama adventure film",  # noqa
                           "https://upload.wikimedia.org/wikipedia/en/2/29/Finding_Nemo.jpg",  # noqa
                           "https://www.youtube.com/watch?v=wZdpNglLbt8",
                           "Andrew Stanton")

# Adding favorite movies to movies list
movies = [minions, forest_gump, finding_nemo]

# Generating and opening the movie page based on the list of movies
fresh_tomatoes.open_movies_page(movies)
