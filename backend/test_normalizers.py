"""Offline tests for route normalization and llm_json fallback behavior."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main


class NormalizerTests(unittest.TestCase):
    def setUp(self):
        self.bank = main.build_bank_fallback(['Python'])
        self.qnorm = main._question_normalizer(['Python'], self.bank)

    def valid_questions(self, result):
        self.assertTrue(main._questions_valid(result), result)
        self.assertEqual(len(result['questions']), 10)
        self.assertEqual([q['id'] for q in result['questions']], list(range(1, 11)))

    def test_question_bare_list_with_string_index_and_option_text(self):
        raw = [{'q':f'Question {i}', 'choices':[' one ', 'two', 'three', 'four', 'extra'],
                'answer_index':'2', 'skill':'not requested'} for i in range(10)]
        result = self.qnorm(raw)
        self.valid_questions(result)
        self.assertEqual(result['questions'][0]['answer_index'], 2)
        self.assertEqual(result['questions'][0]['options'], ['one','two','three','four'])
        self.assertEqual(result['questions'][0]['skill'], 'Python')

    def test_question_wrapper_letter_one_based_and_bank_top_up(self):
        raw = {'mcqs':[{'text':f'Question {i}', 'answers':['a','b','c','d'], 'correct_answer':'B'} for i in range(6)]}
        result = self.qnorm(raw)
        self.valid_questions(result)
        self.assertTrue(all(q['answer_index'] == 1 for q in result['questions'][:6]))
        self.assertEqual(result['questions'][6]['question'], self.bank[0]['question'])

        one_based = {'quiz':[{'question':f'Q {i}', 'options':['a','b','c','d'], 'answer':'3'} for i in range(10)]}
        result = self.qnorm(one_based)
        self.valid_questions(result)
        self.assertTrue(all(q['answer_index'] == 2 for q in result['questions']))

    def test_resume_string_fields(self):
        result = main._resume_normalize({'name':['Jane','Doe'], 'skills':'Python, SQL; Git',
                                         'missing_skills':'Docker', 'match_score':'78/100'})
        self.assertTrue(main._resume_valid(result), result)
        self.assertEqual(result, {'name':'Jane Doe','skills':['Python','SQL','Git'],
                                  'missing_skills':['Docker'],'match_score':78})

    def test_interview_next_alternate_keys_and_boolean(self):
        result = main._next_normalize({'message':'Tell me about your project.', 'done':'false'})
        self.assertTrue(main._next_valid(result), result)
        self.assertEqual(result, {'reply':'Tell me about your project.','done':False})

    def test_interview_score_string_scores(self):
        result = main._score_normalize({'technical':'78/100','hr':'82','soft_skills':'75 points','feedback':['Clear','specific']})
        self.assertTrue(main._score_valid(result), result)
        self.assertEqual(result['technical'],78)
        self.assertEqual(result['hr'],82)
        self.assertEqual(result['soft_skills'],75)
        self.assertIn('Clear', result['feedback'])

    def test_readiness_string_and_plain_items(self):
        normalizer = main._readiness_normalize
        result = normalizer({'readiness_score':'74/100','skill_gaps':[{'skill':'SQL','level':'35'}],
                             'learning_path':['Practice SQL joins']})
        self.assertTrue(self._readiness_valid()(result), result)
        self.assertEqual(result, {'readiness_score':74,'skill_gaps':[{'skill':'SQL','level':35}],
                                  'learning_path':[{'step':'Practice SQL joins','resource':''}]})

    def test_llm_json_uses_normalizer_without_fallback(self):
        content = json.dumps([{'text':f'Question {i}','options':['a','b','c','d'],'answer_index':'A'} for i in range(10)])
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
        with patch.object(main, 'client', client), patch.object(main, 'MODEL_ORDER', ['offline-test']), patch.object(main, 'ACTIVE_MODEL', None):
            result = main.llm_json('system','prompt',{'questions':self.bank}, main._questions_valid, self.qnorm)
        self.valid_questions(result)
        self.assertEqual(result['questions'][0]['answer_index'], 0)

    def test_broken_payload_still_falls_back(self):
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"questions": "nope"}'))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
        fallback = {'questions':self.bank}
        with patch.object(main, 'client', client), patch.object(main, 'MODEL_ORDER', ['offline-test']), patch.object(main, 'ACTIVE_MODEL', None):
            result = main.llm_json('system','prompt',fallback, main._questions_valid, self.qnorm)
        self.assertIs(result, fallback)

    @staticmethod
    def _readiness_valid():
        return lambda x: isinstance(x.get('readiness_score'),int) and isinstance(x.get('skill_gaps'),list) and all(isinstance(g.get('skill'),str) and isinstance(g.get('level'),int) for g in x['skill_gaps']) and isinstance(x.get('learning_path'),list) and all(isinstance(p.get('step'),str) and isinstance(p.get('resource'),str) for p in x['learning_path'])


if __name__ == '__main__':
    unittest.main()
