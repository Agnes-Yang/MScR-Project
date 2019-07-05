import pprint
import sys
import rdflib
from rdflib import Graph

class semantic_reasoning_module:
    def __init__(self, ontology_name, ontology_IRI):
        print("[semantic_reasoning_module][STAT] Starting up... ", end="", flush=True)
        self.ont = self.load_ontology(ontology_name)
        self.ontology_IRI = ontology_IRI
        print("[OK]")

    def start(self, location_classifications, object_activations):
        self.location_classifications = location_classifications
        self.object_activations = object_activations

        num_location_classifications = len(location_classifications)
        num_object_activations = len(object_activations)

        if num_location_classifications != num_object_activations:
            print("[semantic_reasoning_module][ERROR] Number of samples provided for location_classifications and object_activations differ.")
            print("[semantic_reasoning_module][DEBUG] location_classifications:", num_location_classifications, "object_activations: ", num_object_activations)
            return

        activities = []

        for location_classification, object_activation in zip(location_classifications, object_activations):
            first_guess_activities = self.check_location_and_object_agreements(location_classification[0], object_activation)
            print(first_guess_activities)

        # self.module_test()

    def module_test(self):
        print("[semantic_reasoning_module][STAT] Module under test...")
        
        results = self.get_possible_activities_for_location("bedroom_location_bed")
        results = self.get_default_activity_for_location("bedroom_location_bed")
        results = self.get_super_object_of_object("object_coffee_container")
        results = self.get_neighbours_of_location("bedroom_location_bed")
        
        results = self.calculate_dependency_satisfaction("activity_make_hot_drink", ["object_kettle", "object_mug", "object_coffee_container"])

    def load_ontology(self, ontology_name):
        load_name = 'knowledge/' + ontology_name

        ont = Graph()
        ont.parse(load_name)

        return ont

# ***************************
# Core Step Functions
# ***************************

    def check_location_and_object_agreements(self, location_classification, object_activation):
        location_activities = self.get_possible_activities_for_location(location_classification)
        object_activities = []

        for object in object_activation:
            possible_activities = self.get_possible_activities_for_object(object)
            object_activities = object_activities + possible_activities

        agreed_activities = []
        for activity in location_activities:
            if activity in object_activities:
                agreed_activities.append(activity)
        
        reduced_activities = []
        if len(agreed_activities) == 0:
            agreed_activities.append('no_results')
            reduced_activities = agreed_activities
        elif len(agreed_activities) > 1:
            reduced_activities = self.reduce_activities_by_parent(agreed_activities)
        else:
            reduced_activities = agreed_activities

        return reduced_activities

# ***************************
# Ontology Querying Functions
# ***************************

# *** GENERAL

    def add_IRI(self, label):
        ontology_IRI_len = len(self.ontology_IRI)

        potential_IRI = label[:ontology_IRI_len]

        if potential_IRI == self.ontology_IRI:
            label_with_IRI = label
        else:
            label_with_IRI = self.ontology_IRI + label
        
        return label_with_IRI

    def remove_IRI(self, label):
        ontology_IRI_len = len(self.ontology_IRI)

        label_IRI = label[:ontology_IRI_len]

        if label_IRI == self.ontology_IRI:
            label = label[ontology_IRI_len:]

        return label

    def submit_query_single_return(self, subject, predicate, object):
        subject = self.remove_IRI(subject)
        predicate = self.remove_IRI(predicate)
        object = self.remove_IRI(object)

        query = """
            PREFIX sho: <file://sho.owl#>
            SELECT ?""" + object + """
            WHERE { 
                sho:""" + subject + """ sho:""" + predicate +  """ ?""" + object + """
            }
        """

        raw_result = self.ont.query(query)
        print(query)

        results = []
        for row in raw_result:
            results.append(str(getattr(row, object)))

        if len(results) == 0:
            results.append('no_results')

        #  uncomment the line below to see submitted queries
        print(results)

        return results

# *** ACTIVITIY

    def get_possible_activities_for_location(self, location):
        subject = location
        predicate = "hasPossibleActivity"
        object = "activity"

        results = self.submit_query_single_return(subject, predicate, object)

        return results

    def get_default_activity_for_location(self, location):
        subject = location
        predicate = "hasDefaultActivity"
        object = "defaultActivity"

        results = self.submit_query_single_return(subject, predicate, object)

        return results

    def get_possible_activities_for_object(self, leaf_object):
        subject = leaf_object
        predicate = "isPossibleActorIn"
        object = "activity"

        results = self.submit_query_single_return(subject, predicate, object)

        return results

    def get_possible_actors_for_activity(self, activity):
        subject = activity
        predicate = "hasPossibleActor"
        object = "possibleActor"

        results = self.submit_query_single_return(subject, predicate, object)

        return results

    def reduce_activities_by_parent(self, activies):
        parents = []

        for activity in activies:
            super_activity = self.get_super_activity_of_activity(activity)
            parents.append(super_activity)

        parents_reduced = []

        for parent in parents:
            children = parents.count(parent)
            if children > 1 and parent not in parents_reduced:
                parents_reduced = parents_reduced + parent

        for parent in parents_reduced:
            print('parents_reduced', parents_reduced)
            print('parent', parent)
            children = self.get_sub_activities_of_activity(parent)
            for child in children:
                if child in activies:
                    activies.remove(child)

        return activies

    def get_super_activity_of_activity(self, activity):
        subject = activity
        predicate = "subActivityOf"
        object = "superActivity"

        results = self.submit_query_single_return(subject, predicate, object)

        return results

    def get_sub_activities_of_activity(self, activity):
        subject = activity
        predicate = "superActivityOf"
        object = "subActivity"

        results = self.submit_query_single_return(subject, predicate, object)

        return results


# *** OBJECT

    def get_super_object_of_object(self, sub_object):
        subject = sub_object
        predicate = "subObjectOf"
        object = "superObject"

        results = self.submit_query_single_return(subject, predicate, object)

        return results

# *** LOCATION

    def get_neighbours_of_location(self, location):
        subject = location
        predicate = "isNextTo"
        object = "neighbour"

        results = self.submit_query_single_return(subject, predicate, object)

        return results

# *** COMPUTE

    def calculate_dependency_satisfaction(self, activity, objects):
        possible_actors = self.get_possible_actors_for_activity(activity)
        max_actors = len(possible_actors)

        objects_to_add = []
        for object in objects:
            superObject = self.get_super_object_of_object(object)
            if superObject[0] != 'no_results':
                objects_to_add.append(superObject[0])

        objects = objects + objects_to_add

        actor_count = 0

        for object in objects:
            if self.add_IRI(object) in possible_actors:
                actor_count = actor_count + 1

        score = actor_count / max_actors

        print('Score', score)

        return score