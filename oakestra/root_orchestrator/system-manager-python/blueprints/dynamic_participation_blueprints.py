import logging

from bson import json_util
from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from resource_abstractor_client import cluster_operations

dynamic_join_bp = Blueprint("Dynamic Joining", "enabling dynamic participation", url_prefix="/api/dynamic")

worker_join_schema = {
    "type": "object",
    "properties": {
        "worker_ip": {"type": "string"},
        # "worker_location": {"type": "string"},
    },
}

@dynamic_join_bp.route("/register_intent")
class DynamicJoinController(MethodView):
    def post(self, *args, **kwargs):
        """This is the API endpoint which the worker makes first contact with
            when joining the network. It selects a cluster for the worker 
            and sends the cluster information back to the worker.
        """
        data = request.get_json()
        logging.log(logging.INFO, data)

        clusters = list(cluster_operations.get_resources(active=True))
        if clusters is None:
            return abort(500, "Getting clusters failed")
        
        logging.log(logging.INFO, type(clusters))

        chosen_cluster = choose_cluster(clusters)

        response = {
            "cluster_manager_addr": chosen_cluster.get("public_ip"),
            "cluster_manager_port": int(chosen_cluster.get("port"))
        }

        return json_util.dumps(response)
    
def choose_cluster(clusters):
    """This function chooses a cluster for a worker. For now, it is implemented as simply
        as possible. However, as we discuss in the report, we would like to see it 
        implemented in a more intelligent way; e.g., using latency/geographical
        information to choose the most appropriate cluster for the worker. 

        This function is the *policy* for the cluster selection procedure, and is
        separate from the *mechanism*. We describe this in the design chapter when
        we talk about extensibility. 
    """
    return clusters[0]
