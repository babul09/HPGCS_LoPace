import json

def main():
    print("Generating dummy.jsonl with 50000 lines...")
    with open("dummy.jsonl", "w", encoding="utf-8") as f:
        for i in range(50000):
            # Create a somewhat varied string
            if i % 2 == 0:
                s = f"I am a varied prompt. Index number is {i}. Please verify my hash limit boundaries and streaming lengths. This is extra padded tokens text {i*5}."
            else:
                s = f"Totally different string here for index {i} with alternative tokens."
            f.write(json.dumps({"text": s}) + "\n")
    print("Done!")

if __name__ == "__main__":
    main()
