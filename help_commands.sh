
## start master server
# terminal 1
python src/master_server.py

## start minion server 
# terminal 1
python src/minion_server.py --port 8001

# terminal 2
python src/minion_server.py --port 8002

# terminal 3
python src/minion_server.py --port 8003

# terminal 4
python src/minion_server.py --port 8004

# terminal 5
python src/minion_server.py --port 8005

# terminal 6
python src/minion_server.py --port 8006


# send a test request to the master server
curl -X POST "http://localhost:8000/upload-hashes" -F "file=@hashes.txt"

# status of the master server
http://localhost:8000/status





############ for more options ##########
# API docs master server
http://localhost:8000/docs

# API docs minion server
http://localhost:8001/docs



  

