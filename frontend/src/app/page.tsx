'use client';

import Link from 'next/link';

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="bg-blue-600 dark:bg-blue-800 text-white py-4">
        <div className="container mx-auto flex justify-between items-center px-4">
          <h1 className="text-2xl text-white font-bold">Rocket Launch GenAI Platform</h1>
          <div className="space-x-2">
            <Link href="/login">
              <span className="inline-block px-4 py-2 bg-white dark:bg-gray-200 text-blue-600 dark:text-blue-800 rounded-md font-medium hover:bg-gray-100 dark:hover:bg-gray-300">
                Log in
              </span>
            </Link>
            <Link href="/register">
              <span className="inline-block px-4 py-2 bg-blue-700 dark:bg-blue-900 text-white rounded-md font-medium hover:bg-blue-800 dark:hover:bg-blue-950">
                Register
              </span>
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <section className="py-20 bg-gradient-to-b from-blue-100 to-white dark:from-blue-900 dark:to-gray-900">
          <div className="container text-center">
            <h2 className="text-5xl font-bold mb-6 dark:text-white">Modular platform for building AI applications</h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto mb-10">
              Build AI-powered applications quickly and scalably
            </p>
            <div className="flex justify-center gap-4">
              <Link href="">
                <span className="inline-block px-6 py-3 bg-blue-600 dark:bg-blue-700 text-white rounded-md font-medium hover:bg-blue-700 dark:hover:bg-blue-800 text-lg">
                  Try text generation
                </span>
              </Link>
              <Link href="">
                <span className="inline-block px-6 py-3 border border-blue-600 dark:border-blue-500 text-blue-600 dark:text-blue-400 rounded-md font-medium hover:bg-blue-50 dark:hover:bg-blue-900/30 text-lg">
                  View documentation
                </span>
              </Link>
            </div>
          </div>
        </section>

        <section className="py-16 container">
          <h2 className="text-3xl font-bold text-center mb-12 dark:text-white">Main features</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm">
              <h3 className="text-xl font-semibold mb-3 dark:text-white">Event-oriented architecture</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Decoupled communication between components through an event system
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm">
              <h3 className="text-xl font-semibold mb-3 dark:text-white">Integrated RAG system</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Document processing, vectorization, and indexing in Pinecone
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm">
              <h3 className="text-xl font-semibold mb-3 dark:text-white">AI chat engine</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Interaction with language models with support for context and memory
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-gray-100 dark:bg-gray-900 py-8">
        <div className="container text-center text-gray-600 dark:text-gray-400">
          <p>© 2025 Rocket Launch GenAI Platform. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
