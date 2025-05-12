# start master server
python -m master.master_server

# start minion server
python -m minion.minion_server --port 8001

# check if minion is running
curl -X GET "http://localhost:8001/health"

# send a test request to the master server
curl -X POST "http://localhost:8000/upload-hashes" -F "file=@hashes.txt"
