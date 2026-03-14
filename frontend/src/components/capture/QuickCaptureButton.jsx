// QuickCaptureButton.jsx — Floating action button in bottom-right

function QuickCaptureButton({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="
        fixed bottom-6 right-6 z-40
        w-14 h-14 rounded-full
        flex items-center justify-center
        shadow-lg hover:shadow-xl
        transition-all duration-200
        hover:scale-105 active:scale-95
      "
      style={{ backgroundColor: 'var(--color-primary)' }}
      title="Quick capture (⌘N)"
    >
      <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
      </svg>
    </button>
  )
}

export default QuickCaptureButton
