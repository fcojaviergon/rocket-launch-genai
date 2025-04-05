'use client';

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

interface UpgradeNoticeProps {
  className?: string;
}

export const UpgradeNotice: React.FC<UpgradeNoticeProps> = ({ className }) => {
  const [isVisible, setIsVisible] = useState(true);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    // Check if the user has already seen this notice
    const hasSeenNotice = localStorage.getItem('hasSeenUIUpgradeNotice');
    if (hasSeenNotice) {
      setIsVisible(false);
    }
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    // Save in localStorage that the user has seen this notice
    localStorage.setItem('hasSeenUIUpgradeNotice', 'true');
  };

  if (!isMounted || !isVisible) return null;

  return (
    <div className={`bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6 shadow-sm animate-fade-in ${className || ''}`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2h-1V9z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300">
            Improved interface
          </h3>
          <div className="mt-1 text-sm text-blue-700 dark:text-blue-400">
            <p>The interface has been updated to improve contrast, readability, and user experience. If you find any issues, please notify us.</p>
          </div>
        </div>
        <button
          type="button"
          className="flex-shrink-0 ml-3 h-5 w-5 rounded-full inline-flex items-center justify-center text-blue-500 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          onClick={handleDismiss}
        >
          <span className="sr-only">Close</span>
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

export default UpgradeNotice; 