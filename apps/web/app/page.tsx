"use client";

import { useState, useEffect } from "react";

type Question = {
  id: string;
  year: number;
  number: number;
  category: string;
  question_text: string;
  choices: string[];
  correct_answer: number;
  explanation: string;
};

type AttemptHistory = {
  questionId: string;
  selectedAnswer: number;
  isCorrect: boolean;
  answeredAt: string;
};

type LearningHistory = {
  attempts: AttemptHistory[];
};

const STORAGE_KEY = "nurse-exam-history";

function loadHistory(): LearningHistory {
  if (typeof window === "undefined") return { attempts: [] };
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    return JSON.parse(saved);
  }
  return { attempts: [] };
}

function saveHistory(history: LearningHistory) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

export default function Home() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [history, setHistory] = useState<LearningHistory>({ attempts: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setHistory(loadHistory());
    fetch("/data/questions.sample.json")
      .then((res) => {
        if (!res.ok) throw new Error("問題データの読み込みに失敗しました");
        return res.json();
      })
      .then((data: Question[]) => {
        setQuestions(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const currentQuestion = questions[currentIndex];

  const handleSubmit = () => {
    if (selectedAnswer === null || !currentQuestion) return;

    const isCorrect = selectedAnswer === currentQuestion.correct_answer;
    const newAttempt: AttemptHistory = {
      questionId: currentQuestion.id,
      selectedAnswer,
      isCorrect,
      answeredAt: new Date().toISOString(),
    };

    const newHistory = {
      attempts: [...history.attempts, newAttempt],
    };
    setHistory(newHistory);
    saveHistory(newHistory);
    setIsAnswered(true);
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setSelectedAnswer(null);
      setIsAnswered(false);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setSelectedAnswer(null);
      setIsAnswered(false);
    }
  };

  const handleReset = () => {
    setCurrentIndex(0);
    setSelectedAnswer(null);
    setIsAnswered(false);
  };

  const getStats = () => {
    const total = history.attempts.length;
    const correct = history.attempts.filter((a) => a.isCorrect).length;
    const rate = total > 0 ? Math.round((correct / total) * 100) : 0;
    return { total, correct, rate };
  };

  const stats = getStats();
  const isLastQuestion = currentIndex === questions.length - 1;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-600">読み込み中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-red-600">{error}</div>
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-600">問題がありません</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            看護師国家試験 過去問学習
          </h1>
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span>
              解答数: {stats.total} | 正解: {stats.correct} | 正答率:{" "}
              {stats.rate}%
            </span>
          </div>
        </div>

        {/* Progress */}
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>
              問題 {currentIndex + 1} / {questions.length}
            </span>
            <span>{currentQuestion.category}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{
                width: `${((currentIndex + 1) / questions.length) * 100}%`,
              }}
            />
          </div>
        </div>

        {/* Question Card */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-4">
          {/* Question metadata */}
          <div className="text-sm text-gray-500 mb-3">
            第{currentQuestion.year}回 問題{currentQuestion.number}
          </div>

          {/* Question text */}
          <p className="text-lg text-gray-900 mb-6 leading-relaxed">
            {currentQuestion.question_text}
          </p>

          {/* Choices */}
          <div className="space-y-3">
            {currentQuestion.choices.map((choice, index) => {
              const isSelected = selectedAnswer === index;
              const isCorrect = index === currentQuestion.correct_answer;
              const showResult = isAnswered;

              let buttonClass =
                "w-full text-left p-4 rounded-lg border-2 transition-all ";

              if (showResult) {
                if (isCorrect) {
                  buttonClass +=
                    "border-green-500 bg-green-50 text-green-900";
                } else if (isSelected && !isCorrect) {
                  buttonClass += "border-red-500 bg-red-50 text-red-900";
                } else {
                  buttonClass +=
                    "border-gray-200 bg-gray-50 text-gray-500";
                }
              } else {
                if (isSelected) {
                  buttonClass +=
                    "border-blue-500 bg-blue-50 text-blue-900";
                } else {
                  buttonClass +=
                    "border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700";
                }
              }

              return (
                <button
                  key={index}
                  onClick={() => !isAnswered && setSelectedAnswer(index)}
                  disabled={isAnswered}
                  className={buttonClass}
                >
                  <span className="font-medium mr-2">{index + 1}.</span>
                  {choice}
                  {showResult && isCorrect && (
                    <span className="ml-2 text-green-600 font-bold">
                      (正解)
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Submit button */}
          {!isAnswered && (
            <button
              onClick={handleSubmit}
              disabled={selectedAnswer === null}
              className="mt-6 w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              解答する
            </button>
          )}

          {/* Result & Explanation */}
          {isAnswered && (
            <div className="mt-6">
              {/* Result banner */}
              <div
                className={`p-4 rounded-lg mb-4 ${
                  selectedAnswer === currentQuestion.correct_answer
                    ? "bg-green-100 text-green-800"
                    : "bg-red-100 text-red-800"
                }`}
              >
                <span className="font-bold text-lg">
                  {selectedAnswer === currentQuestion.correct_answer
                    ? "正解!"
                    : "不正解"}
                </span>
              </div>

              {/* Explanation */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="font-bold text-gray-900 mb-2">解説</h3>
                <p className="text-gray-700 leading-relaxed">
                  {currentQuestion.explanation}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex gap-3">
          <button
            onClick={handlePrevious}
            disabled={currentIndex === 0}
            className="flex-1 py-3 px-4 bg-white border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            前の問題
          </button>

          {isAnswered && !isLastQuestion && (
            <button
              onClick={handleNext}
              className="flex-1 py-3 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              次の問題へ
            </button>
          )}

          {isAnswered && isLastQuestion && (
            <button
              onClick={handleReset}
              className="flex-1 py-3 px-4 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
            >
              最初から
            </button>
          )}

          {!isAnswered && (
            <button
              onClick={handleNext}
              disabled={isLastQuestion}
              className="flex-1 py-3 px-4 bg-white border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              スキップ
            </button>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500">
          学習履歴はブラウザに保存されます
        </div>
      </div>
    </div>
  );
}
