import os
import sys
import argparse
from multiprocessing import Process
from dotenv import load_dotenv
from by_framework.worker import run_worker

# 导入所有 Worker 类
from orchestrator import HierarchicalOrchestrator
from research_team import ResearchTeamWorker
from coder_team import CoderTeamWorker

load_dotenv()

def start_worker(worker_class, worker_id):
    """启动单个 Worker 进程"""
    print(f"🚀 Starting {worker_class.__name__} (ID: {worker_id})...")
    run_worker(
        worker_class,
        worker_id=worker_id,
        redis_host=os.getenv("BYAI_REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("BYAI_REDIS_PORT", 6379)),
        redis_db=int(os.getenv("BYAI_REDIS_DB", 0)),
        redis_username=os.getenv("BYAI_REDIS_USERNAME"),
        redis_password=os.getenv("BYAI_REDIS_PASSWORD"),
    )

def main():
    parser = argparse.ArgumentParser(description="Agent Teams Framework Sample")
    parser.add_argument(
        "role", 
        choices=["orchestrator", "research", "coder", "all"], 
        help="Specify which role to start"
    )
    args = parser.parse_args()

    if args.role == "orchestrator":
        start_worker(HierarchicalOrchestrator, "orchestrator-1")
    elif args.role == "research":
        start_worker(ResearchTeamWorker, "research-team-1")
    elif args.role == "coder":
        start_worker(CoderTeamWorker, "coder-team-1")
    elif args.role == "all":
        print("🌟 Starting full Software Development Center (3 nodes)...")
        processes = []
        
        # 启动三个进程
        roles = [
            (HierarchicalOrchestrator, "orchestrator-1"),
            (ResearchTeamWorker, "research-team-1"),
            (CoderTeamWorker, "coder-team-1"),
        ]
        
        for worker_class, worker_id in roles:
            p = Process(target=start_worker, args=(worker_class, worker_id))
            p.start()
            processes.append(p)
            
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down all workers...")
            for p in processes:
                p.terminate()

if __name__ == "__main__":
    main()
