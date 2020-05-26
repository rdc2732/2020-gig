Records = [('Cyber','12345'),('Cyber','12346'),('Okapi','123457'),('Okapi','123458'),('Okapi','123459'),('Magic','123460'),('Magic','123461'),('SIC','123462')]
Team = ""
Feature = ""

for t,f in Records:
    if Team == "":
        Team = t
    if t != Team:
        Feature = f
        print("A", Team, Feature)
        Team = t
    else:
        print("B", Team, Feature)
print("C", Team, Feature)
