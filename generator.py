from random import shuffle, randrange, choice
import json
with open(r"D:\Data\Dev\Teky\CHAPTER I\_FINAL-PROJECT_\preset data\Names.txt", 'r', encoding='utf-8') as file:
    names = file.read().split('\n')
shuffle(names)
data = {}
def student():
    def grade() -> str:
        return str(randrange(60, 100, 5) / 10)

    return {
        'giới tính': choice(['Nam', 'Nữ']),
        'văn': grade(),
        'toán': grade(),
        'anh': grade()
    }


for class_index in range(1, 6):
    class_name = 'Lớp 9.' + str(class_index)
    data[class_name] = {names.pop(): student() for _ in range(5)}

with open('data.json', 'w', encoding='utf-8') as file:
    json.dump(data, file, indent=4, ensure_ascii=False)