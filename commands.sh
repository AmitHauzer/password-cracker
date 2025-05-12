# start master server
python master/master_server.py

# start minion server
python minion/minion_server.py --host 0.0.0.0 --port 8001

# check if minion is running
curl -X GET "http://localhost:8001/health"
