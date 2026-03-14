// GreetingCard.jsx — Time-based greeting

function GreetingCard() {
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 17) return 'Good afternoon'
    return 'Good evening'
  }

  const formatDate = () => {
    return new Date().toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    })
  }

  return (
    <div className="mb-8">
      <h1 
        className="text-3xl font-bold mb-1"
        style={{ color: 'var(--color-text)' }}
      >
        {getGreeting()}
      </h1>
      <p style={{ color: 'var(--color-text-secondary)' }}>
        {formatDate()}
      </p>
    </div>
  )
}

export default GreetingCard
