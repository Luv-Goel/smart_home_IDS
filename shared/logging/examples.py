import asyncio
from shared.logging.setup import setup_logging, get_logger
from shared.logging.tracing import set_correlation_id

# Initialize logging for the application
setup_logging(log_level="DEBUG", json_format=True)

logger = get_logger(__name__)


async def process_task(task_id: int):
    # Set correlation ID for this async task context
    set_correlation_id(f"task-{task_id}")

    logger.info("starting_task", task_id=task_id)

    try:
        if task_id == 2:
            raise ValueError("Task 2 simulates a failure")
        await asyncio.sleep(0.1)
        logger.info("task_completed", task_id=task_id, status="success")
    except Exception as e:
        logger.error("task_failed", task_id=task_id, exc_info=e)


async def main():
    logger.info("application_started")

    # Run tasks concurrently; each gets its own correlation ID
    await asyncio.gather(process_task(1), process_task(2), process_task(3))

    logger.info("application_finished")


if __name__ == "__main__":
    asyncio.run(main())
