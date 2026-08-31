#!/bin/bash
cd /opt/data/.tmp_tests
python3 finalize_movies.py 2>&1
echo "MOVIE_FINALIZE_DONE"
