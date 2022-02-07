from faker import Faker
fake = Faker("en_NG") # not available

with open("output.txt","w") as f:
    for i in range(100):
        f.write(fake.unique.name())