import asyncio
import time

async def simulate(total_assignments, concurrency):
    average_req_time = 0.5  # Asumsi 1 request = 500ms
    # Kalau concurrency 5, artinya kita bisa selesai 5 request dlm 500ms
    requests_per_second = concurrency / average_req_time
    total_seconds = total_assignments / requests_per_second
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    print(f"Total: {total_assignments} assignments")
    print(f"Concurrency: {concurrency}")
    print(f"Requests per second: {requests_per_second}")
    print(f"Estimated time: {hours} hours, {minutes} minutes")

if __name__ == "__main__":
    asyncio.run(simulate(300000, 5))
    print("---")
    asyncio.run(simulate(300000, 15))
    print("---")
    asyncio.run(simulate(300000, 30))
