import asyncio
import unittest
from typing import Any, cast

from app.services.autonomy.topic_bus import (
    SubscriptionClosed,
    Topic,
    TopicBus,
    TopicDefinitionError,
)


class TestTopicDefinition(unittest.TestCase):
    def test_requires_canonical_absolute_topic_name(self) -> None:
        for name in ["scan", "/", "/scan/", "/lidar//scan"]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    Topic(name, int)


class TestTopicBus(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bus = TopicBus()
        self.topic = Topic("/test/value", int)

    async def test_publish_fans_out_to_independent_subscribers(self) -> None:
        first = self.bus.subscribe(self.topic, max_queue_size=2)
        second = self.bus.subscribe(self.topic, max_queue_size=2)

        self.bus.publish(self.topic, 7)

        self.assertEqual(await first.get(), 7)
        self.assertEqual(await second.get(), 7)
        self.assertEqual(self.bus.stats(self.topic).subscribers, 2)

    async def test_slow_subscriber_drops_oldest_without_blocking_publisher(
        self,
    ) -> None:
        subscription = self.bus.subscribe(self.topic, max_queue_size=2)

        for value in [1, 2, 3]:
            self.bus.publish(self.topic, value)

        self.assertEqual(subscription.get_nowait(), 2)
        self.assertEqual(subscription.get_nowait(), 3)
        self.assertEqual(subscription.dropped_messages, 1)
        stats = self.bus.stats(self.topic)
        self.assertEqual(stats.published_messages, 3)
        self.assertEqual(stats.delivered_messages, 3)
        self.assertEqual(stats.dropped_messages, 1)

    async def test_latest_value_can_be_replayed_to_late_subscriber(self) -> None:
        self.bus.publish(self.topic, 10)

        replaying = self.bus.subscribe(self.topic)
        non_replaying = self.bus.subscribe(self.topic, replay_latest=False)

        self.assertEqual(replaying.get_nowait(), 10)
        self.assertEqual(non_replaying.pending_messages, 0)
        self.assertEqual(self.bus.latest(self.topic), 10)

    async def test_non_retained_topic_does_not_replay(self) -> None:
        transient = Topic("/test/transient", str, retain_latest=False)
        self.bus.publish(transient, "event")

        subscription = self.bus.subscribe(transient)

        self.assertEqual(subscription.pending_messages, 0)
        self.assertIsNone(self.bus.latest(transient))

    async def test_rejects_wrong_message_type_at_runtime(self) -> None:
        with self.assertRaisesRegex(TypeError, "requires int"):
            self.bus.publish(self.topic, cast(Any, "wrong"))

    async def test_rejects_conflicting_definition_for_same_name(self) -> None:
        self.bus.subscribe(self.topic)

        with self.assertRaises(TopicDefinitionError):
            self.bus.subscribe(Topic("/test/value", str))

    async def test_closing_subscription_unblocks_waiting_consumer(self) -> None:
        subscription = self.bus.subscribe(self.topic)
        waiting = asyncio.create_task(subscription.get())

        subscription.close()

        with self.assertRaises(SubscriptionClosed):
            await waiting
        self.assertEqual(self.bus.stats(self.topic).subscribers, 0)

    async def test_bus_close_ends_async_iteration_and_rejects_new_work(self) -> None:
        subscription = self.bus.subscribe(self.topic)

        self.bus.close()

        with self.assertRaises(StopAsyncIteration):
            await subscription.__anext__()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.bus.publish(self.topic, 1)
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.bus.subscribe(self.topic)

    async def test_sensor_thread_can_schedule_publication_safely(self) -> None:
        subscription = self.bus.subscribe(self.topic)

        await asyncio.to_thread(self.bus.publish_threadsafe, self.topic, 42)

        self.assertEqual(await asyncio.wait_for(subscription.get(), timeout=1), 42)


if __name__ == "__main__":
    unittest.main()
