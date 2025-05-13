# start master server
python src/master_server.py

# start minion server
python src/minion_server.py --port 8001

# check if minion is running
curl -X GET "http://localhost:8001/health"

# send a test request to the master server
curl -X POST "http://localhost:8000/upload-hashes" -F "file=@hashes.txt"

# get a task for a minion to process
curl -X GET "http://localhost:8000/get-task?minion_id=minion-8001"

# status of the master server
curl -X GET "http://localhost:8000/status"  

