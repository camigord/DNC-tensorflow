import tensorflow as tf
import numpy as np
import unittest
import shutil
import os

from dnc.dnc import DNC
from dnc.memory import Memory
from dnc.controller import BaseController

class DummyController(BaseController):
    def network_vars(self):
        self.W = tf.Variable(tf.truncated_normal([self.nn_input_size, 64]), name='layer_W')
        self.b = tf.Variable(tf.zeros([64]), name='layer_b')

    def network_op(self, X):
        return tf.matmul(X, self.W) + self.b


class DNCTest(unittest.TestCase):

    @classmethod
    def _clear(cls):
        try:
            current_dir = os.path.dirname(__file__)
            ckpts_dir = os.path.join(current_dir, 'checkpoints')

            shutil.rmtree(ckpts_dir)
        except:
            # swallow error
            return

    @classmethod
    def setUpClass(cls):
        cls._clear()


    @classmethod
    def tearDownClass(cls):
        cls._clear()


    def test_construction(self):
        graph = tf.Graph()
        with graph.as_default():
            with tf.Session(graph=graph) as session:

                computer = DNC(DummyController, 10, 20, 10, 10, 64, 1)

                self.assertEqual(computer.input_size, 10)
                self.assertEqual(computer.output_size, 20)
                self.assertEqual(computer.words_num, 10)
                self.assertEqual(computer.word_size, 64)
                self.assertEqual(computer.read_heads, 1)
                self.assertEqual(computer.batch_size, 1)

                self.assertTrue(isinstance(computer.memory, Memory))
                self.assertTrue(isinstance(computer.controller, DummyController))


    def test_call(self):
        graph = tf.Graph()
        with graph.as_default():
            with tf.Session(graph=graph) as session:

                computer = DNC(DummyController, 10, 20, 10, 10, 64, 2, batch_size=3)
                input_batches = np.random.uniform(0, 1, (3, 5, 10)).astype(np.float32)

                session.run(tf.initialize_all_variables())
                out, view = session.run(computer.get_outputs(), feed_dict={
                    computer.input_data: input_batches,
                    computer.sequence_length: 5
                })

                M, L, u, p, r, wr, ww = session.run([
                    computer.memory.memory_matrix,
                    computer.memory.link_matrix,
                    computer.memory.usage_vector,
                    computer.memory.precedence_vector,
                    computer.memory.read_vectors,
                    computer.memory.read_weightings,
                    computer.memory.write_weighting
                ])

                self.assertEqual(out.shape, (3, 5, 20))
                self.assertEqual(view['free_gates'].shape, (3, 5, 2))
                self.assertEqual(view['allocation_gates'].shape, (3, 5, 1))
                self.assertEqual(view['write_gates'].shape, (3, 5, 1))
                self.assertEqual(view['read_weightings'].shape, (3, 5, 10, 2))
                self.assertEqual(view['write_weightings'].shape, (3, 5, 10))

                self.assertFalse(np.array_equal(M, np.zeros((3, 10, 64), dtype=np.float32)))
                self.assertFalse(np.array_equal(L, np.zeros((3, 10, 10), dtype=np.float32)))
                self.assertFalse(np.array_equal(u, np.zeros((3, 10), dtype=np.float32)))
                self.assertFalse(np.array_equal(p, np.zeros((3, 10), dtype=np.float32)))
                self.assertFalse(np.array_equal(r, np.zeros((3, 64, 2), dtype=np.float32)))
                self.assertFalse(np.array_equal(wr, np.zeros((3, 10, 2), dtype=np.float32)))
                self.assertFalse(np.array_equal(ww, np.zeros((3, 10), dtype=np.float32)))


    def test_save(self):
        graph = tf.Graph()
        with graph.as_default():
            with tf.Session(graph=graph) as session:

                computer = DNC(DummyController, 10, 20, 10, 10, 64, 2, batch_size=2)
                session.run(tf.initialize_all_variables())
                current_dir = os.path.dirname(__file__)
                ckpts_dir = os.path.join(current_dir, 'checkpoints')

                computer.save(session, ckpts_dir, 'test-save')

                self.assert_(True)


    def test_restore(self):

        current_dir = os.path.dirname(__file__)
        ckpts_dir = os.path.join(current_dir, 'checkpoints')

        model1_output, model1_memview = None, None
        sample_input = np.random.uniform(0, 1, (2, 5, 10)).astype(np.float32)
        sample_seq_len = 5

        graph1 = tf.Graph()
        with graph1.as_default():
            with tf.Session(graph=graph1) as session1:

                computer = DNC(DummyController, 10, 20, 10, 10, 64, 2, batch_size=2)
                session1.run(tf.initialize_all_variables())

                saved_weights = session1.run([
                    computer.controller.nn_output_weights,
                    computer.controller.interface_weights,
                    computer.controller.mem_output_weights,
                    computer.controller.W,
                    computer.controller.b
                ])

                computer.save(session1, ckpts_dir, 'test-restore')

        graph2 = tf.Graph()
        with graph2.as_default():
            with tf.Session(graph=graph2) as session2:

                computer = DNC(DummyController, 10, 20, 10, 10, 64, 2, batch_size=2)
                session2.run(tf.initialize_all_variables())
                computer.restore(session2, ckpts_dir, 'test-restore')

                restored_weights = session2.run([
                    computer.controller.nn_output_weights,
                    computer.controller.interface_weights,
                    computer.controller.mem_output_weights,
                    computer.controller.W,
                    computer.controller.b
                ])

                self.assertTrue(np.product([np.array_equal(restored_weights[i], saved_weights[i]) for i in range(5)]))

if __name__ == '__main__':
    unittest.main(verbosity=2)