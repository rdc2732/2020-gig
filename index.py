list1 = [1,3,5,6,8,90]
for item in list1:
    idx = list1.index(item)
    if idx > 0:
        print(list1[idx-1],item)
